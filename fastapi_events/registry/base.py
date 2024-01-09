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
