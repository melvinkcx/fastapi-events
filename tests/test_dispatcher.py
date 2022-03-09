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


@pytest.mark.parametrize(
    "suppress_events",
    (True,
     False))
def test_suppression_of_events(
    suppress_events, mocker,
):
    """
    Test if dispatch() can be disabled properly with
    `FASTAPI_EVENTS_DISABLE_DISPATCH` environment variable.

    It should be enabled by default.
    """
    if suppress_events:
        mocker.patch.dict(os.environ, {"FASTAPI_EVENTS_DISABLE_DISPATCH": "1"})

    spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")

    dispatch("TEST_EVENT")

    assert spy_event_store_ctx_var.get.called != suppress_events


@pytest.mark.parametrize(
    "event_payload,should_raise_error",
    (({"user_id": uuid.uuid4(), "created_at": datetime.utcnow()}, False),
     ({"user_id": uuid.uuid4()}, True),
     ({}, True),
     (None, True)))
def test_payload_validation_with_pydantic(
    event_payload, should_raise_error, mocker
):
    """
    Test if event payloads are properly validated when a payload schema is registered.
    """
    payload_schema = EventPayloadSchemaRegistry()
    spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")

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
        assert spy_event_store_ctx_var.get.called


def test_dispatching_without_payload_schema(
    mocker
):
    """
    Test if dispatch() works fine when no payload schema is registered
    """
    spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")

    dispatch("TEST_EVENT", {"id": uuid.uuid4()})

    assert spy_event_store_ctx_var.get.called
