import asyncio
import contextlib
from collections import deque
from contextvars import Token
from typing import Deque, Iterable, Iterator

from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi_events import (event_store, handler_store, is_handling_events,
                            middleware_identifier)
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


class EventHandlerASGIMiddleware:
    def __init__(self, app: ASGIApp, handlers: Iterable[BaseEventHandler]) -> None:
        self.app = app
        self._id = id(self)
        self.register_handlers(handlers=handlers)

    def register_handlers(self, handlers: Iterable[BaseEventHandler]) -> None:
        handler_store[self._id] = handlers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        with self.event_store_ctx():
            try:
                await self.app(scope, receive, send)
            finally:
                with self.is_handling_events_ctx():
                    await self._process_events()

    @contextlib.contextmanager
    def event_store_ctx(self) -> Iterator[None]:
        token: Token = event_store.set(deque())

        try:
            yield
        finally:
            event_store.reset(token)

    @contextlib.contextmanager
    def is_handling_events_ctx(self) -> Iterator[None]:
        """
        Context manager to set:
        - is_handling_events
        - middleware_identifier
        """
        token_is_handling_events: Token = is_handling_events.set(True)
        token_middleware_id: Token = middleware_identifier.set(self._id)

        try:
            yield
        finally:
            is_handling_events.reset(token_is_handling_events)
            middleware_identifier.reset(token_middleware_id)

    async def _process_events(self) -> None:
        handlers = handler_store[self._id]
        q: Deque[Event] = event_store.get()

        await asyncio.gather(*[handler.handle_many(events=q)
                               for handler in handlers])
