import asyncio
import functools
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import pydantic
import pytest

import fastapi_events.dispatcher as dispatcher_module
from fastapi_events import BaseEventHandler, handler_store
from fastapi_events.constants import FASTAPI_EVENTS_DISABLE_DISPATCH_ENV_VAR
from fastapi_events.dispatcher import dispatch
from fastapi_events.registry.payload_schema import EventPayloadSchemaRegistry
from fastapi_events.typing import Event

pytest_plugins = (
    "tests.fixtures.otel",
)


@pytest.fixture
def setup_mocks_for_events_in_req_res_cycle(mocker):
    def setup(
        disable_dispatch: bool,
        in_req_res_cycle: bool = True
    ):
        if disable_dispatch:
            mocker.patch.dict(os.environ, {FASTAPI_EVENTS_DISABLE_DISPATCH_ENV_VAR: "1"})

        mocker.patch("fastapi_events.dispatcher.in_req_res_cycle").get.return_value = in_req_res_cycle

        spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")

        return locals()

    return setup


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suppress_events",
    (True,
     False))
async def test_suppression_of_events_in_req_res_cycle(
    suppress_events, setup_mocks_for_events_in_req_res_cycle,
):
    """
    Test if dispatch() can be disabled properly with
    `FASTAPI_EVENTS_DISABLE_DISPATCH` environment variable.

    It should be enabled by default.
    """
    mocks = setup_mocks_for_events_in_req_res_cycle(disable_dispatch=suppress_events)

    dispatch("TEST_EVENT")

    assert mocks["spy_event_store_ctx_var"].get.called != suppress_events


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_payload,should_raise_error",
    (({"user_id": uuid.uuid4(), "created_at": datetime.utcnow()}, False),
     ({"user_id": uuid.uuid4()}, True),
     ({}, True),
     (None, True)))
async def test_payload_validation_with_pydantic_in_req_res_cycle(
    event_payload, should_raise_error, setup_mocks_for_events_in_req_res_cycle
):
    """
    Test if event payloads are properly validated when a payload schema is registered.
    """
    payload_schema = EventPayloadSchemaRegistry()
    mocks = setup_mocks_for_events_in_req_res_cycle(disable_dispatch=False)

    class UserEvents(Enum):
        SIGNED_UP = "USER_SIGNED_UP"

    @payload_schema.register(event_name=UserEvents.SIGNED_UP)
    class _SignUpEventSchema(pydantic.BaseModel):
        user_id: uuid.UUID  # type: ignore[annotation-unchecked]
        created_at: datetime  # type: ignore[annotation-unchecked]

    dispatch_fn = functools.partial(dispatch,
                                    event_name=UserEvents.SIGNED_UP,
                                    payload=event_payload,
                                    payload_schema_registry=payload_schema)

    if should_raise_error:
        with pytest.raises(pydantic.ValidationError):
            dispatch_fn()

    else:
        dispatch_fn()
        assert mocks["spy_event_store_ctx_var"].get.called


@pytest.mark.asyncio
async def test_dispatching_without_payload_schema_in_req_res_cycle(
    setup_mocks_for_events_in_req_res_cycle
):
    """
    Test if dispatch() works fine when no payload schema is registered
    """
    mocks = setup_mocks_for_events_in_req_res_cycle(disable_dispatch=False)

    dispatch("TEST_EVENT", {"id": uuid.uuid4()})

    assert mocks["spy_event_store_ctx_var"].get.called


@pytest.fixture
def setup_mocks_for_events_outside_req_res_cycle(mocker):
    def setup(
        disable_dispatch: bool,
        in_req_res_cycle: bool = False,
        mock__dispatch_as_task: bool = False,
        middleware_id: Optional[int] = None,
    ):
        if disable_dispatch:
            mocker.patch.dict(os.environ, {FASTAPI_EVENTS_DISABLE_DISPATCH_ENV_VAR: "1"})

        mocker.patch("fastapi_events.dispatcher.in_req_res_cycle").get.return_value = in_req_res_cycle

        spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")
        spy__list_handlers = mocker.spy(dispatcher_module, "_list_handlers")
        spy__dispatch_as_task = mocker.spy(dispatcher_module, "_dispatch_as_task")

        if mock__dispatch_as_task:
            mock__dispatch_as_task = mocker.patch("fastapi_events.dispatcher._dispatch_as_task")

        if middleware_id:
            mocker.patch("fastapi_events.dispatcher.middleware_identifier").get.return_value = middleware_id

        return locals()

    return setup


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suppress_events",
    (True,
     False))
async def test_suppression_of_events_outside_req_res_cycle(
    suppress_events, setup_mocks_for_events_outside_req_res_cycle
):
    """
    Test if dispatch() can be disabled properly with
    `FASTAPI_EVENTS_DISABLE_DISPATCH` environment variable.
    """
    mocks = setup_mocks_for_events_outside_req_res_cycle(
        disable_dispatch=suppress_events,
        mock__dispatch_as_task=True)

    dispatch("TEST_EVENT")

    assert mocks["mock__dispatch_as_task"].called != suppress_events
    assert not mocks["spy_event_store_ctx_var"].get.called


@pytest.mark.asyncio
async def test_dispatching_outside_req_res_cycle(
    setup_mocks_for_events_outside_req_res_cycle
):
    """
    Test if tasks are properly dispatched outside of request-response cycle
    """

    class FakeEventHandler(BaseEventHandler):
        is_handled = False

        async def handle(self, event: Event) -> None:
            self.is_handled = True

    middleware_id, handler = uuid.uuid4().int, FakeEventHandler()
    handler_store[middleware_id] = [handler]
    mocks = setup_mocks_for_events_outside_req_res_cycle(
        disable_dispatch=False,
        middleware_id=middleware_id)

    dispatch("TEST_EVENT")

    assert mocks["spy__list_handlers"].spy_return == [handler]
    assert isinstance(mocks["spy__dispatch_as_task"].spy_return, asyncio.Task)

    await asyncio.sleep(0.1)

    assert mocks["spy__dispatch_as_task"].spy_return.done()
    assert handler.is_handled


@pytest.mark.asyncio
async def test_otel_support(
    otel_test_manager, setup_mocks_for_events_in_req_res_cycle
):
    """
    Test if OTEL span is properly created when dispatch() is called
    """
    setup_mocks_for_events_in_req_res_cycle(disable_dispatch=True)

    dispatch("TEST_EVENT")

    spans_created = otel_test_manager.get_finished_spans()
    assert spans_created[0].name == "Event TEST_EVENT dispatched"
