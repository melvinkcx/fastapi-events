from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.echo import EchoHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware

app = Starlette(middleware=[
    Middleware(EventHandlerASGIMiddleware,
               handlers=[EchoHandler()])
])
client = TestClient(app)


@app.route("/")
async def root(request: Request) -> JSONResponse:
    dispatch(event_name="new event", payload={"id": 1})
    return JSONResponse()


def test_event_handling(mocker):
    handler_spy = mocker.spy(EchoHandler, "handle")

    client.get("/")

    assert handler_spy.called
    assert handler_spy.call_args[0][1] == ("new event", {"id": 1})
