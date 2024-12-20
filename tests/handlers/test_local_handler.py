from enum import Enum
from typing import Callable, Tuple
from unittest.mock import MagicMock

import pytest
from fastapi import Depends
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.local import LocalHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.otel.attributes import SpanAttributes
from fastapi_events.typing import Event

pytest_plugins = (
    "tests.fixtures.otel",
)


@pytest.fixture
def setup_test() -> Callable:
    def setup() -> Tuple[Starlette, LocalHandler]:
        handler = LocalHandler()
        app = Starlette(middleware=[Middleware(EventHandlerASGIMiddleware, handlers=[handler])])

        @app.route("/events")
        async def root(request: Request) -> JSONResponse:
            dispatch(event_name=request.query_params["event"],
                     payload={})
            return JSONResponse([])

        return app, handler

    return setup


def test_local_handler(
    setup_test
):
    """
    Test local handler with a mix of functions and coroutines (async)
    """
    app, handler = setup_test()

    event_to_be_dispatched = ("cat_ate_a_fish",
                              "cat_requested_something",
                              "dog_asked_for_petting",
                              "dog_finished_the_food",
                              "dad_made_beet_juice",
                              "juice_is_spoiled",
                              "she_danced_with_her_partner")
    events_handled = {event_name: []
                      for event_name in ("cat", "all", "dog", "juice", "dance")}

    @handler.register(event_name="cat_*")
    async def handle_all_cat_events(event: Event):
        events_handled["cat"].append(event)

    @handler.register
    def handle_all_events(event: Event):
        events_handled["all"].append(event)

    @handler.register(event_name="dog_*")
    async def handle_all_dog_events(event: Event):
        events_handled["dog"].append(event)

    @handler.register(event_name="*juice")
    def handle_all_juice_events(event: Event):
        events_handled["juice"].append(event)

    @handler.register(event_name="*dance*")
    async def handle_all_dance_events(event: Event):
        events_handled["dance"].append(event)

    @app.route("/")
    async def root(request: Request) -> JSONResponse:
        for event_name in event_to_be_dispatched:
            dispatch(event_name=event_name)

        return JSONResponse([])

    client = TestClient(app)
    for event in event_to_be_dispatched:
        client.get(f"/events?event={event}")

    for event_category, expected_count in (
        ("cat", 2),
        ("all", 7),
        ("dog", 2),
        ("juice", 1),  # `juice_is_spoiled` is not matching `*juice`
        ("dance", 1)
    ):
        assert len(events_handled[event_category]) == expected_count


def test_local_handler_with_enum(
    setup_test
):
    """
    Test local_handler with Enum as event name
    """
    app, handler = setup_test()

    class Events(Enum):
        CREATED = "CREATED"

    events_handled = []

    @handler.register(event_name=Events.CREATED)
    async def handle_all_created_events(event: Event):
        events_handled.append(event)

    @app.route("/events/enum_type")
    async def root(request: Request) -> JSONResponse:
        dispatch(Events.CREATED)
        return JSONResponse([])

    client = TestClient(app)
    client.get("/events/enum_type")

    assert events_handled[0][0] == Events.CREATED


def test_chain_registration_of_local_handler(
    setup_test
):
    """
    Test if we can chain multiple `@local_handler.register`

    Eg:
        @local_handler.register(event_name=Events.CREATED)
        @local_handler.register(event_name=Events.UPDATED)
        async def handler(event: Event):
            pass

    """
    app, handler = setup_test()

    events_handled = []
    all_events = ("user_created", "user_updated")

    @handler.register(event_name="user_created")
    @handler.register(event_name="user_updated")
    async def handle_events(event: Event):
        events_handled.append(event)

    client = TestClient(app)

    for event in all_events:
        client.get(f"/events?event={event}")

    assert tuple(event for event, _ in events_handled) == all_events


def test_otel_support(
    otel_test_manager, setup_test
):
    """
    Test if OTEL span is properly created when the event is handled
    """
    app, handler = setup_test()

    @handler.register(event_name="TEST_EVENT")
    async def handle_events(event: Event):
        ...

    client = TestClient(app)
    client.get("/events?event=TEST_EVENT")

    spans_created = otel_test_manager.get_finished_spans()
    assert spans_created[-1].name == "handling event TEST_EVENT with LocalHandler"
    assert spans_created[-1].attributes[SpanAttributes.HANDLER] == "fastapi_events.handlers.local.LocalHandler"


def test_local_handler_with_async_fastapi_dependencies(
    setup_test
):
    """
    to verify the support of async FastAPI dependencies
    Relevant Github issue: #41
    """
    app, handler = setup_test()

    _mock_db = MagicMock()
    _mock_service_client = MagicMock()

    async def get_db():
        return _mock_db

    async def get_service_client():
        return _mock_service_client

    @handler.register(event_name="TEST_EVENT")
    async def handle_event_with_dependency(
        event: Event,
        db=Depends(get_db),
        service_client=Depends(get_service_client)
    ):
        assert db == _mock_db
        assert service_client == _mock_service_client

    client = TestClient(app)
    client.get("/events?event=TEST_EVENT")


def test_local_handler_with_nested_async_dependencies(
    setup_test
):
    """
    to verify the support of nested async FastAPI dependencies
    Relevant Github issue: #41
    """
    app, handler = setup_test()

    _mock_service_client = MagicMock()
    _mock_db = MagicMock()
    _mock_connection_pool = MagicMock()

    async def get_connection_pool():
        return _mock_connection_pool

    async def get_db(
        connection_pool=Depends(get_connection_pool)
    ):
        return _mock_db, connection_pool

    async def get_service_client():
        return _mock_service_client

    @handler.register(event_name="TEST_EVENT")
    async def handle_event_with_dependency(
        event: Event,
        db=Depends(get_db),
        service_client=Depends(get_service_client)
    ):
        assert db == (_mock_db, _mock_connection_pool)
        assert service_client == _mock_service_client

    client = TestClient(app)
    client.get("/events?event=TEST_EVENT")


def test_local_handler_with_sync_fastapi_dependencies(
    setup_test
):
    """
    to verify the support of sync FastAPI dependencies
    Relevant Github issue: #60
    """
    app, handler = setup_test()

    _mock_dependency = MagicMock()

    def get_repo():
        return _mock_dependency

    @handler.register(event_name="TEST_EVENT")
    async def handle_event_with_sync_dependency(
        event: Event,
        repo=Depends(get_repo)
    ):
        assert repo == _mock_dependency

    client = TestClient(app)
    client.get("/events?event=TEST_EVENT")
