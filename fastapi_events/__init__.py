from contextvars import ContextVar

__version__ = "0.2.0"

event_store = ContextVar("fastapi_context")
