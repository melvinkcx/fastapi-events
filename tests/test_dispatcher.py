import functools
import os
import uuid
from datetime import datetime
from enum import Enum

import pydantic
import pytest

import fastapi_events.dispatcher as dispatcher_module
from fastapi_events.dispatcher import dispatch
from fastapi_events.registry.payload_schema import EventPayloadSchemaRegistry


@pytest.fixture
def setup_mocks(mocker):
    def setup(
        disable_dispatch: bool,
        in_req_res_cycle: bool
    ):
        if disable_dispatch:
            mocker.patch.dict(os.environ, {"FASTAPI_EVENTS_DISABLE_DISPATCH": "1"})

        mocker.patch("fastapi_events.dispatcher.in_req_res_cycle").get.return_value = in_req_res_cycle

        spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")

        return locals()

    return setup


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suppress_events",
    (True,
     False))
async def test_suppression_of_events(
    suppress_events, setup_mocks,
):
    """
    Test if dispatch() can be disabled properly with
    `FASTAPI_EVENTS_DISABLE_DISPATCH` environment variable.

    It should be enabled by default.
    """
    mocks = setup_mocks(disable_dispatch=suppress_events,
                        in_req_res_cycle=True)

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
    event_payload, should_raise_error, setup_mocks
):
    """
    Test if event payloads are properly validated when a payload schema is registered.
    """
    payload_schema = EventPayloadSchemaRegistry()
    mocks = setup_mocks(disable_dispatch=False,
                        in_req_res_cycle=True)

    class UserEvents(Enum):
        SIGNED_UP = "USER_SIGNED_UP"

    @payload_schema.register(event_name=UserEvents.SIGNED_UP)
    class _SignUpEventSchema(pydantic.BaseModel):
        user_id: uuid.UUID
        created_at: datetime

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
    setup_mocks
):
    """
    Test if dispatch() works fine when no payload schema is registered
    """
    mocks = setup_mocks(disable_dispatch=False,
                        in_req_res_cycle=True)

    dispatch("TEST_EVENT", {"id": uuid.uuid4()})

    assert mocks["spy_event_store_ctx_var"].get.called
