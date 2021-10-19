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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        token = event_store.set(deque())
        try:
            await self.app(scope, receive, send)
        finally:
            await self._process_events()
        event_store.reset(token)

    async def _process_events(self) -> None:
        q: Deque[Event] = event_store.get()
        await asyncio.gather(*[handler.handle_many(events=q)
                               for handler in self._handlers])
