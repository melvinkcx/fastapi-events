import asyncio
from contextlib import suppress
from typing import List

import pytest
from starlite.app import Starlite
from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import get
from starlite.middleware import DefineMiddleware
from starlite.response import Response
from starlite.testing import create_test_client

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.typing import Event


@pytest.mark.parametrize(
    "return_non_200,raise_error,add_global_exception_handler",
    ((True, False, None),
     (False, False, None),
     (False, True, True),
     (False, True, False))
)
def test_event_handling(
    return_non_200, raise_error, add_global_exception_handler
):
    """
    Making sure events are handled regardless of response status, and exceptions
    This is unlike how BackgroundTask works.
    """

    class DummyHandler(BaseEventHandler):
        def __init__(self):
            self.event_processed = []

        async def handle(self, event: Event) -> None:
            self.event_processed.append(event)

    dummy_handler_1 = DummyHandler()
    dummy_handler_2 = DummyHandler()

    @get(path="/", media_type=MediaType.JSON)
    async def root() -> Response[List]:
        for idx in range(5):
            dispatch(event_name="new event", payload={"id": idx + 1})

        if raise_error:
            raise ValueError

        return Response(content=[], status_code=400 if return_non_200 else 200)

    exception_handlers = {}
    if add_global_exception_handler:
        def global_exception_handler(request, exc):
            HTTPException(content="[]", status_code=500)

        exception_handlers[ValueError] = global_exception_handler

    client = create_test_client(
        exception_handlers=exception_handlers,
        middleware=[
            DefineMiddleware(
                EventHandlerASGIMiddleware,
                handlers=[dummy_handler_1, dummy_handler_2],
            ),
        ],
        route_handlers=[root],
    )

    with suppress(ValueError):
        client.get("/")

    assert len(dummy_handler_1.event_processed) == len(dummy_handler_2.event_processed) == 5


@pytest.mark.parametrize(
    "middleware_id",
    ((None),
     (1234),
     (1337))
)
@pytest.mark.asyncio
async def test_event_handling_without_request(middleware_id):
    """
    Making sure events are handled when dispatched with an explicit middleware_id
    """

    class DummyHandler(BaseEventHandler):
        def __init__(self):
            self.event_processed = []

        async def handle(self, event: Event) -> None:
            self.event_processed.append(event)

    dummy_handler_1 = DummyHandler()
    dummy_handler_2 = DummyHandler()

    Starlite(
        middleware=[
            DefineMiddleware(
                EventHandlerASGIMiddleware,
                handlers=[dummy_handler_1, dummy_handler_2],
                middleware_id=middleware_id,
            ),
        ],
        route_handlers=[],
    )

    if middleware_id is None:
        with pytest.raises(LookupError, match=r"^<ContextVar name='fastapi_middleware_identifier' at"):
            dispatch(event_name="new event", payload={"id": "fail"}, middleware_id=middleware_id)
    else:
        for idx in range(5):
            dispatch(event_name="new event", payload={"id": idx + 1}, middleware_id=middleware_id)

        # allow time for events to be dispatched
        await asyncio.sleep(0.1)

        assert len(dummy_handler_1.event_processed) == len(dummy_handler_2.event_processed) == 5
