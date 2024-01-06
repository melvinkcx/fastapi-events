import asyncio
import contextlib
import logging
import os
from contextvars import Token
from enum import Enum
from typing import Any, Deque, Dict, Iterable, Iterator, Optional, Union

from fastapi_events import (BaseEventHandler, event_store, handler_store,
                            in_req_res_cycle, middleware_identifier)
from fastapi_events.constants import FASTAPI_EVENTS_DISABLE_DISPATCH_ENV_VAR
from fastapi_events.errors import (MissingEventNameDuringDispatch,
                                   MultiplePayloadsDetectedDuringDispatch)
from fastapi_events.otel.utils import (create_span_for_dispatch_fn,
                                       inject_traceparent)
from fastapi_events.registry.base import BaseEventPayloadSchemaRegistry
from fastapi_events.registry.payload_schema import \
    registry as default_payload_schema_registry
from fastapi_events.typing import Event
from fastapi_events.utils import strtobool

try:
    import pydantic  # noqa: F401

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS = {"exclude_unset": True}

logger = logging.getLogger(__name__)


def _list_handlers() -> Iterable[BaseEventHandler]:
    """
    Get registered handlers from the global handler_store with middleware_identifier
    """
    middleware_id: int = middleware_identifier.get()
    return handler_store[middleware_id]


def _dispatch_as_task(event_name: Union[str, Enum], payload: Optional[Any] = None) -> asyncio.Task:
    """
    #23 To support event chaining
    - dispatch event and schedule its handling as an asyncio.Task
    """
    handlers = _list_handlers()

    async def task():
        await asyncio.gather(*[handler.handle((event_name, payload)) for handler in handlers])

    return asyncio.create_task(task())


def _dispatch(event_name: Union[str, Enum], payload: Optional[Any] = None) -> None:
    """
    The main dispatcher function.
    - Setting FASTAPI_EVENTS_DISABLE_DISPATCH to any truthy value essentially disables event dispatching of all sorts
    """
    DISABLE_DISPATCH_GLOBALLY = strtobool(os.environ.get(FASTAPI_EVENTS_DISABLE_DISPATCH_ENV_VAR, "0"))

    if DISABLE_DISPATCH_GLOBALLY:
        logger.debug("Dispatch function is disabled globally. "
                     "If you believe this is a mistake, "
                     "please make sure the environment variable '%s' is not set.",
                     FASTAPI_EVENTS_DISABLE_DISPATCH_ENV_VAR)
        return

    is_handling_request: bool = in_req_res_cycle.get()
    if is_handling_request:
        logger.debug("Event dispatched within a request-response cycle. "
                     "Enqueing event to event store...")
        q: Deque[Event] = event_store.get()
        q.append((event_name, payload))

    else:
        logger.debug("Event is dispatched outside of a request-response cycle."
                     "Dispatching event as an asyncio.Task...")
        _dispatch_as_task(event_name, payload)


@contextlib.contextmanager
def _set_middleware_identifier(middleware_id: int) -> Iterator[None]:
    token_middleware_id: Token = middleware_identifier.set(middleware_id)
    try:
        yield
    finally:
        middleware_identifier.reset(token_middleware_id)


def dispatch(
    event_name_or_model: Union[str, Enum, Any] = None,
    payload: Optional[Any] = None,
    event_name: Union[str, Enum] = None,  # this will be prioritized
    validate_payload: bool = True,
    payload_schema_cls_dict_args: Optional[Dict[str, Any]] = None,
    payload_schema_registry: Optional[BaseEventPayloadSchemaRegistry] = None,
    middleware_id: Optional[int] = None
) -> None:
    """
    A wrapper of the main dispatcher function with additional checks.

    Steps:
    1. set `event_name` if event name is passed as the first positional argument
    2. check if the first positional argument is a pydantic model
        - if so,
    3. validate event payload with schema registered:
        - only when the payload is a dict or None
        - only when pydantic is available
        - only when a payload schema has been registered with the event
    4. check if event dispatching has been disabled, return if so
    5. check if dispatch is called within the request-response cycle:
        5.1. if so, append the event into the event_store context var
        5.2. if not, create a Task to handle the event with handlers registered
    """
    # Handle invalid arguments
    # If event model, event name and payload are provided at the same time,
    # we won't know which payload to take.
    if all((
        event_name_or_model and not isinstance(event_name_or_model, (str, Enum)),
        payload  # can be {}
    )):
        raise MultiplePayloadsDetectedDuringDispatch

    # Handle dispatch without event_name specified
    if not event_name and isinstance(event_name_or_model, (str, Enum)):
        event_name = event_name_or_model

    with create_span_for_dispatch_fn(event_name=event_name):
        if HAS_PYDANTIC:
            # Handle dispatch of pydantic Model
            if isinstance(event_name_or_model, pydantic.BaseModel):
                if not event_name:
                    event_name = getattr(event_name_or_model, "__event_name__", None)

                if not event_name:
                    raise MissingEventNameDuringDispatch

                if not payload:
                    payload_schema_cls_dict_args = payload_schema_cls_dict_args or DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS
                    payload = event_name_or_model.dict(**payload_schema_cls_dict_args)

            # Validate event payload with schema registered
            elif (isinstance(payload, dict) or not payload) and validate_payload:
                logger.debug("Pydantic is enabled. Validating payload schema...")
                if not payload_schema_registry:
                    payload_schema_registry = default_payload_schema_registry

                payload_schema_cls = payload_schema_registry.get(event_name)
                if payload_schema_cls:
                    payload_schema_cls_dict_args = payload_schema_cls_dict_args or DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS
                    payload = payload_schema_cls(**(payload or {})).dict(**payload_schema_cls_dict_args)
                else:
                    logger.debug("Payload schema for event %s not found. Skipping validation...", event_name)

        # OTEL
        if payload and isinstance(payload, dict):
            logger.debug("Injecting traceparent to event payload...")
            inject_traceparent(payload=payload)

        # Environment-specific handling
        if middleware_id:
            with _set_middleware_identifier(middleware_id):
                return _dispatch(event_name=event_name, payload=payload)
        else:
            return _dispatch(event_name=event_name, payload=payload)
