from contextvars import ContextVar

__version__ = "0.3.0"

event_store: ContextVar = ContextVar("fastapi_context")
