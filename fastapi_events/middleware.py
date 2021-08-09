from starlette.background import BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from fastapi_events.dispatcher import dispatch
from fastapi_events.handler import handle


class EventHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.dispatch = dispatch

        response = await call_next(request)

        if not response.background:
            response.background = BackgroundTasks()

        response.background.add_task(handle)

        return response
