from contextvars import ContextVar

__version__ = "0.1.2"

event_store = ContextVar("fastapi_context")
