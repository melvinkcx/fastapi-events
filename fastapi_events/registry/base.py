import logging
from abc import ABCMeta
from collections import UserDict
from typing import Optional, Type

from fastapi_events.errors import MissingEventNameDuringRegistration

logger = logging.getLogger(__name__)

BaseModel: Optional[Type] = None
try:
    from pydantic import BaseModel
except ImportError:
    logger.warning("Pydantic is required to use schema registry")


class BaseEventPayloadSchemaRegistry(UserDict, metaclass=ABCMeta):
    """
    A mapping storing event name and its associated Pydantic schema
    It is used by `dispatch()` to validate in event payload it receives.
    """

    def register(self, _schema=None, event_name=None):
        """
        Registers a payload schema, used to validate event payload during dispatch.
        Schemas must be a subclass of `pydantic.BaseModel`.

        ### Args

        :param _schema: A Pydantic schema to be registered. Typically, you would use `register` as a decorator and omit this argument.
        :param event_name: The name of the event to be associated with the schema. If provided, overrides the `__event_name__` attribute of the schema.

        ### Exceptions

        :raises MissingEventNameDuringRegistration: If `event_name` is not provided and the schema does not have an `__event_name__` attribute.
        :raises AssertionError: If the schema is not a subclass of `pydantic.BaseModel`.

        ### Examples

        Provide an event name as a decorator argument:
        ```python
        from fastapi_events.registry.payload_schema import registry

        @registry.register(event_name="my_event")
        class MyEventPayloadSchema(pydantic.BaseModel):
            id: int
            name: str
        ```

        Or use the `__event_name__` attribute in the schema to have the event name inferred from the schema itself:
        ```python
        @registry.register
        class MyEventPayloadSchema(pydantic.BaseModel):
            __event_name__ = "my_event"
            id: int
            name: str
        ```
        """

        def _derive_event_name(_schema):
            """
            this modifies `event_name` in the scope
            """
            nonlocal event_name

            if not event_name:
                event_name = getattr(_schema, "__event_name__", None)

            if not event_name:
                raise MissingEventNameDuringRegistration

        def _wrap(schema):
            if BaseModel and not issubclass(schema, BaseModel):
                raise AssertionError("'schema' must be a subclass of Pydantic BaseModel")

            _derive_event_name(_schema=schema)
            self.data[event_name] = schema

            return schema

        if _schema is None:
            return _wrap

        _derive_event_name(_schema=_schema)
        self.data[event_name] = _schema

        return _schema
