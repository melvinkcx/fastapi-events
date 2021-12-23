from contextvars import ContextVar

__version__ = "0.2.2"

event_store: ContextVar = ContextVar("fastapi_context")
