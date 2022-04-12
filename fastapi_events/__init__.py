from collections import defaultdict
from contextvars import ContextVar
from typing import Dict, Iterable

from fastapi_events.handlers.base import BaseEventHandler

__version__ = "0.3.0"  # TODO bump to 0.4.0

# handlers keeps track of all handlers registered via EventHandlerASGIMiddleware
handler_store: Dict[int, Iterable[BaseEventHandler]] = defaultdict(list)

# event_store keeps track of all events dispatched the request-response cycle
event_store: ContextVar = ContextVar("fastapi_event_store")

# is_handling_events is set before event processing starts
is_handling_events: ContextVar = ContextVar("fastapi_is_handling_events", default=None)
middleware_identifier: ContextVar = ContextVar("fastapi_middleware_identifier")
