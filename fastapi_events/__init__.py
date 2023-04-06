from collections import defaultdict
from contextvars import ContextVar
from typing import Dict, Iterable

from fastapi_events.handlers.base import BaseEventHandler

__version__ = "0.9.0"

# handlers keeps track of all handlers registered via EventHandlerASGIMiddleware
handler_store: Dict[int, Iterable[BaseEventHandler]] = defaultdict(list)

# event_store keeps track of all events dispatched the request-response cycle
event_store: ContextVar = ContextVar("fastapi_event_store")

# in_req_res_cycle is set to allow dispatch() to work in event handlers
in_req_res_cycle: ContextVar = ContextVar("fastapi_in_req_res_cycle", default=None)

# middleware_identifier is to allow dispatch() to retrieve a list of handlers that
# are associated with the middleware instance that processed the events
middleware_identifier: ContextVar = ContextVar("fastapi_middleware_identifier")
