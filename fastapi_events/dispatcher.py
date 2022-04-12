import asyncio
import os
from distutils.util import strtobool
from enum import Enum
from typing import Any, Deque, Dict, Optional, Union

from fastapi_events import (event_store, handler_store, is_handling_events,
                            middleware_identifier)
from fastapi_events.registry.base import BaseEventPayloadSchemaRegistry
from fastapi_events.registry.payload_schema import \
    registry as default_payload_schema_registry
from fastapi_events.typing import Event

try:
    import pydantic  # noqa: F401

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS = {"exclude_unset": True}


def _dispatch_as_task(event_name: Union[str, Enum], payload: Optional[Any] = None) -> None:
    """
    TODO #23 Implement event chaining
    """
    middleware_id: int = middleware_identifier.get()
    handlers = handler_store[middleware_id]

    async def task():
        await asyncio.gather(*[handler.handle((event_name, payload)) for handler in handlers])

    asyncio.create_task(task())


def _dispatch(event_name: Union[str, Enum], payload: Optional[Any] = None) -> None:
    """
    The main dispatcher function.
    - Setting FASTAPI_EVENTS_DISABLE_DISPATCH to any truthy value essentially disables event dispatching of all sorts
    """
    DISABLE_DISPATCH_GLOBALLY = strtobool(os.environ.get("FASTAPI_EVENTS_DISABLE_DISPATCH", "0"))

    if DISABLE_DISPATCH_GLOBALLY:
        return

    # TODO #23
    in_handling_mode: bool = is_handling_events.get()
    if in_handling_mode:
        _dispatch_as_task(event_name, payload)

    else:
        q: Deque[Event] = event_store.get()
        q.append((event_name, payload))


def dispatch(
    event_name: Union[str, Enum],
    payload: Optional[Any] = None,
    validate_payload: bool = True,
    payload_schema_cls_dict_args: Optional[Dict[str, Any]] = None,
    payload_schema_registry: Optional[BaseEventPayloadSchemaRegistry] = None
) -> None:
    """
    A wrapper of the main dispatcher function with additional checks:
    - It validates the payload against Pydantic schema registered. It will be deactivated if Pydantic is not installed.
    """

    # Validate event payload with schema registered
    if HAS_PYDANTIC and validate_payload:
        if not payload_schema_registry:
            payload_schema_registry = default_payload_schema_registry

        payload_schema_cls = payload_schema_registry.get(event_name)
        if payload_schema_cls:
            payload_schema_cls_dict_args = payload_schema_cls_dict_args or DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS
            payload = payload_schema_cls(**(payload or {})).dict(**payload_schema_cls_dict_args)

    return _dispatch(event_name=event_name, payload=payload)
