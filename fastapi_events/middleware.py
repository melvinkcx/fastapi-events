import asyncio
from collections import deque
from contextvars import Token
from typing import Optional, Deque, Iterable

from starlette.types import ASGIApp, Scope, Receive, Send

from fastapi_events import event_store
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


class EventHandlerASGIMiddleware:
    def __init__(self, app: ASGIApp, handlers: Iterable[BaseEventHandler]) -> None:
        self.app = app
        self._handlers: Iterable[BaseEventHandler] = handlers
        self._token: Optional[Token] = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        self._initialize_event_store()
        try:
            await self.app(scope, receive, send)
        finally:
            await self._process_events()
            self._teardown_event_store()

    async def _process_events(self) -> None:
        q: Deque[Event] = event_store.get()

        async def execute(handler):
            if hasattr(handler, "handle_many") and callable(handler.handle_many):
                await handler.handle_many(q)
            else:
                await asyncio.gather(*[handler.handle(event) for event in q])

        await asyncio.gather(*[execute(handler) for handler in self._handlers])

    def _initialize_event_store(self) -> None:
        self._token = event_store.set(deque())

    def _teardown_event_store(self) -> None:
        event_store.reset(self._token)
