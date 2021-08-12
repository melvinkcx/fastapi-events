from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

import fastapi_events.middleware
from fastapi_events.dispatcher import dispatch
from fastapi_events.middleware import EventHandlerMiddleware

app = Starlette(middleware=[Middleware(EventHandlerMiddleware)])
client = TestClient(app)


@app.route("/")
async def root(request: Request) -> JSONResponse:
    dispatch(event_name="a_new_event")
    return JSONResponse()


def test_event_handling(mocker):
    handler_spy = mocker.spy(fastapi_events.middleware, "handle_events")

    client.get("/")

    assert handler_spy.called
