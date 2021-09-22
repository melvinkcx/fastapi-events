from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.local import local_handler
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.typing import Event


def test_local_handler():
    """
    Test local handler with a mix of functions and coroutines (async)
    """
    event_to_be_dispatched = ("cat_ate_a_fish",
                              "cat_requested_something",
                              "dog_asked_for_petting",
                              "dog_finished_the_food",
                              "dad_made_beet_juice",
                              "juice_is_spoiled",
                              "she_danced_with_her_partner")
    events_handled = {event_name: []
                      for event_name in ("cat", "all", "dog", "juice", "dance")}

    @local_handler.register(event_name="cat_*")
    async def handle_all_cat_events(event: Event):
        events_handled["cat"].append(event)

    @local_handler.register(event_name="*")
    def handle_all_events(event: Event):
        events_handled["all"].append(event)

    @local_handler.register(event_name="dog_*")
    async def handle_all_dog_events(event: Event):
        events_handled["dog"].append(event)

    @local_handler.register(event_name="*juice")
    def handle_all_juice_events(event: Event):
        events_handled["juice"].append(event)

    @local_handler.register(event_name="*dance*")
    async def handle_all_dance_events(event: Event):
        events_handled["dance"].append(event)

    app = Starlette(middleware=[
        Middleware(EventHandlerASGIMiddleware,
                   handlers=[local_handler])])

    @app.route("/")
    async def root(request: Request) -> JSONResponse:
        for event_name in event_to_be_dispatched:
            dispatch(event_name=event_name)

        return JSONResponse()

    client = TestClient(app)
    client.get("/")

    for event_category, expected_count in (
        ("cat", 2),
        ("all", 7),
        ("dog", 2),
        ("juice", 1),  # `juice_is_spoiled` is not matching `*juice`
        ("dance", 1)
    ):
        assert len(events_handled[event_category]) == expected_count
