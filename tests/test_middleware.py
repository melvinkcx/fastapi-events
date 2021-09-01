import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.typing import Event


class DummyHandler(BaseEventHandler):
    def __init__(self):
        self.event_processed = []

    async def handle(self, event: Event) -> None:
        self.event_processed.append(event)


@pytest.mark.parametrize("return_error", [True, False])
def test_event_handling(return_error):
    """
    Making sure events are handled regardless of response status
    This is unlike how BackgroundTask works.
    """
    dummy_handler_1 = DummyHandler()
    dummy_handler_2 = DummyHandler()

    app = Starlette(middleware=[
        Middleware(EventHandlerASGIMiddleware,
                   handlers=[dummy_handler_1, dummy_handler_2])])

    @app.route("/")
    async def root(request: Request) -> JSONResponse:
        for idx in range(5):
            dispatch(event_name="new event", payload={"id": idx + 1})

        return JSONResponse(status_code=400 if return_error else 200)

    client = TestClient(app)
    client.get("/")

    assert len(dummy_handler_1.event_processed) == len(dummy_handler_2.event_processed) == 5
