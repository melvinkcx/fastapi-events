from enum import Enum

import pydantic
import pytest

from fastapi_events.errors import MissingEventNameDuringRegistration
from fastapi_events.registry.payload_schema import EventPayloadSchemaRegistry


class UserEvents(Enum):
    SIGNED_UP = "USER_SIGNED_UP"


class _SignUpEventSchema(pydantic.BaseModel):
    username: str


class _SignUpEventSchemaWithEventName(_SignUpEventSchema):
    __event_name__: str = "USER_SIGNED_UP"


@pytest.fixture
def registry():
    return EventPayloadSchemaRegistry()


@pytest.mark.parametrize(
    "event_name",
    (UserEvents.SIGNED_UP,
     "USER_SIGNED_UP",)
)
def test_schema_registration_with_explicit_event_name(
    event_name, registry
):
    """
    Event name provided explicitly (both of string and enum type)
    """
    registry.register(event_name=event_name)(_SignUpEventSchema)

    assert registry[event_name] == _SignUpEventSchema


def test_schema_registration_with_event_name_from_schema_1(
    registry
):
    """
    Event name defined in schema as the value of __event_name__
    """

    @registry.register()
    class Schema(_SignUpEventSchemaWithEventName):
        ...

    assert registry[Schema.__event_name__] \
           == registry["USER_SIGNED_UP"] \
           == Schema


def test_schema_registration_with_event_name_from_schema_2(
    registry
):
    """
    Event name defined in schema as the value of __event_name__
    """

    @registry.register
    class Schema(_SignUpEventSchemaWithEventName):
        ...

    assert registry[Schema.__event_name__] \
           == registry["USER_SIGNED_UP"] \
           == Schema


def test_schema_registration_without_event_name(
    registry
):
    """
    MissingEventNameDuringRegistration should be raised
    when event_name is not provided and __event_name__ is not defined.
    """
    with pytest.raises(MissingEventNameDuringRegistration):
        @registry.register  # event_name is not provided
        class Schema(pydantic.BaseModel):
            # __event_name__ is not provided
            ...

    assert len(registry) == 0
