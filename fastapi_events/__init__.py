from contextvars import ContextVar

__version__ = "0.1.3"

event_store = ContextVar("fastapi_context")
