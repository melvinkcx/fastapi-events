from collections import deque
from contextvars import Token

from starlette.types import ASGIApp, Scope, Receive, Send

from fastapi_events import event_store
from fastapi_events.handler import handle_events


class EventHandlerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ["http", "websocket"]:
            await self.app(scope, receive, send)
            return

        token: Token = event_store.set(deque())
        try:
            await self.app(scope, receive, send)
        finally:
            handle_events()
            event_store.reset(token)
