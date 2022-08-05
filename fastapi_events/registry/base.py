import logging
from abc import ABCMeta
from collections import UserDict
from typing import Optional, Type

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
        if not event_name:
            raise ValueError("'event_name' must be provided when registering a schema")

        def _wrap(schema):
            if BaseModel and not issubclass(schema, BaseModel):
                raise AssertionError("'schema' must be a subclass of Pydantic BaseModel")

            self.data[event_name] = schema
            return schema

        if _schema is None:
            return _wrap

        return _schema
