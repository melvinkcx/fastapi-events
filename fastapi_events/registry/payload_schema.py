import logging

from fastapi_events.registry.base import BaseEventPayloadSchemaRegistry

logger = logging.getLogger(__name__)


class EventPayloadSchemaRegistry(BaseEventPayloadSchemaRegistry):
    pass


registry = EventPayloadSchemaRegistry()
