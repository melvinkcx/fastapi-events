import asyncio
import contextlib
import logging
from collections import deque
from contextvars import Token
from typing import Deque, Iterable, Iterator, Optional

from fastapi_events import (event_store, handler_store, in_req_res_cycle,
                            middleware_identifier)
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import ASGIApp, Event, Receive, Scope, Send

logger = logging.getLogger(__name__)


class EventHandlerASGIMiddleware:
    def __init__(self, app: ASGIApp, handlers: Iterable[BaseEventHandler], middleware_id: Optional[int] = None) -> None:
        self.app = app
        self._id = id(self) if middleware_id is None else middleware_id
        self.register_handlers(handlers=handlers)

    def __del__(self):
        """
        Removing handlers after middleware is necessary when `self._id` == `id(self)`
        """
        if self._id == id(self):
            self.deregister_handlers()

    def register_handlers(self, handlers: Iterable[BaseEventHandler]) -> None:
        handler_store[self._id] = handlers

    def deregister_handlers(self) -> None:
        del handler_store[self._id]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        with self.event_store_ctx():
            try:
                with self.res_req_cycle_ctx():
                    await self.app(scope, receive, send)
            finally:
                await self._process_events()

    @contextlib.contextmanager
    def event_store_ctx(self) -> Iterator[None]:
        logger.debug("Setting event_store ctx")

        token_middleware_id: Token = middleware_identifier.set(self._id)
        token_event_store: Token = event_store.set(deque())

        try:
            yield
        finally:
            logger.debug("Resetting event_store ctx")
            event_store.reset(token_event_store)
            middleware_identifier.reset(token_middleware_id)

    @contextlib.contextmanager
    def res_req_cycle_ctx(self) -> Iterator[None]:
        token_is_res_req_cycle: Token = in_req_res_cycle.set(True)

        try:
            yield
        finally:
            in_req_res_cycle.reset(token_is_res_req_cycle)

    async def _process_events(self) -> None:
        handlers = handler_store[self._id]
        q: Deque[Event] = event_store.get()

        logger.debug("Processing events")
        await asyncio.gather(*[handler.handle_many(events=q)
                               for handler in handlers])
