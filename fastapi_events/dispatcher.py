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
from fastapi_events.typing import Event, EventName, Payload, PydanticModel
from fastapi_events.utils import strtobool

IS_PYDANTIC_V1 = False
try:
    import pydantic  # noqa: F401

    HAS_PYDANTIC = True
    IS_PYDANTIC_V1 = pydantic.VERSION.startswith("1.")
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


def _check_for_multiple_payloads(
    event_name_or_model: Union[EventName, PydanticModel],
    payload: Payload
):
    """
    Check if multiple payloads are provided.
    If event model, event name and payload are provided at the same time,
    we won't know which payload to take.
    """
    if all((
        event_name_or_model and not isinstance(event_name_or_model, (str, Enum)),
        payload  # can be {}
    )):
        raise MultiplePayloadsDetectedDuringDispatch


def _derive_event_name_and_payload_from_pydantic_model(
    event_name_or_model: Union[EventName, PydanticModel],
    event_name: EventName,
    payload: Payload,
    payload_schema_cls_dict_args: Dict[str, Any],
    payload_schema_dump: bool
):
    """
    Derive event_name and payload from Pydantic model
    """
    if not event_name:
        event_name = getattr(event_name_or_model, "__event_name__", None)

    if not event_name:
        raise MissingEventNameDuringDispatch

    if not payload:
        payload_schema_cls_dict_args = payload_schema_cls_dict_args or DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS
        if payload_schema_dump:
            if IS_PYDANTIC_V1:
                payload = event_name_or_model.dict(**payload_schema_cls_dict_args)
            else:
                payload = event_name_or_model.model_dump(**payload_schema_cls_dict_args)
        else:
            payload = event_name_or_model

    return event_name, payload


def _validate_payload(
    event_name: EventName,
    payload: Payload,
    payload_schema_registry: BaseEventPayloadSchemaRegistry,
    payload_schema_cls_dict_args: Dict[str, Any],
    payload_schema_dump: bool = True
):
    """
    Validate payload if a corresponding payload schema is registered
    """
    if not payload_schema_registry:
        payload_schema_registry = default_payload_schema_registry

    payload_schema_cls = payload_schema_registry.get(event_name)
    if payload_schema_cls:
        payload_schema_cls_dict_args = payload_schema_cls_dict_args or DEFAULT_PAYLOAD_SCHEMA_CLS_DICT_ARGS
        deserialized_payload = payload_schema_cls(**(payload or {}))
        if payload_schema_dump:
            if IS_PYDANTIC_V1:
                payload = deserialized_payload.dict(**payload_schema_cls_dict_args)
            else:
                payload = deserialized_payload.model_dump(**payload_schema_cls_dict_args)
        else:
            payload = deserialized_payload
    else:
        logger.debug("Payload schema for event %s not found. Skipping validation...", event_name)

    return payload


def dispatch(
    event_name_or_model: Union[EventName, Any] = None,
    payload: Optional[Any] = None,
    event_name: EventName = None,  # this will be prioritized
    validate_payload: bool = True,
    payload_schema_cls_dict_args: Optional[Dict[str, Any]] = None,
    payload_schema_registry: Optional[BaseEventPayloadSchemaRegistry] = None,
    middleware_id: Optional[int] = None,
    payload_schema_dump: bool = True
) -> None:
    """
    Dispatches an event. This is a wrapper of the main dispatcher function with additional checks.

    ### Args

    :param event_name_or_model: Event name or pydantic model. If `event_name` is not provided, \
        the event name will be derived from the model's `__event_name__` attribute.
    :param payload: Event payload.
    :param event_name: Event name. If provided, overrides the event name derived from the event model.
    :param validate_payload: Validate payload with its registered payload schema. Pydantic payloads \
        are dumped and re-instantiated.
    :param payload_schema_cls_dict_args: A dict of args passed to the pydantic dump function. Defaults \
        to `{"exclude_unset": True}`. See \
        [pydantic v1](https://docs.pydantic.dev/1.10/usage/exporting_models/#modeldict) or \
        [pydantic v2](https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_dump) \
        docs for more details.
    :param payload_schema_registry: Optional payload schema registry. If omitted, the default registry \
        will be used.
    :param middleware_id: Optional custom middleware identifier.
    :param payload_schema_dump: Dump pydantic model payloads and validated payloads to dict before \
        calling event handlers.

    ### Exceptions

    :raises MultiplePayloadsDetectedDuringDispatch: If `event_name_or_model` is a pydantic model and \
        `payload` is provided.
    :raises MissingEventNameDuringDispatch: If `event_name` is not provided and the event model does \
        not have an `__event_name__` attribute.

    ### Examples

    Events have a name and optional payload. The payload can be any python object.
    ```python
    from fastapi_events.dispatcher import dispatch

    # With a string event name and dict payload (payload has no validation)
    dispatch("user_created", {"user_id": 1})
    ```

    Register a payload schema with the event name to validate the payload.
    ```python
    from fastapi_events.registry.payload_schema import registry

    @registry.register("user_created")
    class UserCreated(pydantic.BaseModel):
        user_id: int

    # The payload will be validated with the registered payload schema
    dispatch("user_created", {"user_id": 1})
    ```

    Alternatively, the payload can be a pydantic model instance. The payload will be dumped to dict \
        before being passed to handlers.
    - If `validate_payload` is True, it will be re-instantiated using the registered payload schema \
        before being dumped to dict again.
    - If `payload_schema_dump` is False, the payload will be passed to handlers as an instance of the \
        payload schema.
    - Set both to false if you want to pass the payload instance untouched to the handlers.

    ```python
    dispatch("user_created", UserCreated(user_id=1))
    ```

    If a pydantic model is passed as the payload, the event name will be derived from the model's \
        `__event_name__` attribute.
    ```python
    class UserCreated(pydantic.BaseModel):
        __event_name__ = "user_created"
        user_id: int

    dispatch(UserCreated(user_id=1))
    ```

    Providing an explicit event name will override the derived event name from the model.
    ```python
    class UserCreated(pydantic.BaseModel):
        __event_name__ = "user_created"
        user_id: int

    # `__event_name__` will be overridden, and only handlers for "user_updated" will be called.
    dispatch(UserCreated(user_id=1), event_name="user_updated")
    ```
    """
    # Handle invalid arguments
    _check_for_multiple_payloads(event_name_or_model=event_name_or_model, payload=payload)

    # Handle dispatch without event_name specified
    if not event_name and isinstance(event_name_or_model, (str, Enum)):
        event_name = event_name_or_model
    elif hasattr(event_name_or_model, "__event_name__"):
        event_name = event_name_or_model.__event_name__

    with create_span_for_dispatch_fn(event_name=event_name):
        if HAS_PYDANTIC:
            # Handle dispatch of pydantic Model
            if isinstance(event_name_or_model, pydantic.BaseModel):
                logger.debug("Pydantic model is passed as the payload. Deriving event_name, and payload from it...")
                event_name, payload = _derive_event_name_and_payload_from_pydantic_model(
                    event_name_or_model=event_name_or_model,
                    event_name=event_name,
                    payload=payload,
                    payload_schema_cls_dict_args=payload_schema_cls_dict_args,
                    payload_schema_dump=payload_schema_dump,
                )

            # Validate event payload with schema registered
            elif (isinstance(payload, dict) or not payload) and validate_payload:
                logger.debug("Pydantic is enabled. Validating payload schema...")
                payload = _validate_payload(
                    event_name=event_name,
                    payload=payload,
                    payload_schema_registry=payload_schema_registry,
                    payload_schema_cls_dict_args=payload_schema_cls_dict_args,
                    payload_schema_dump=payload_schema_dump
                )

        # OTEL
        if payload:
            logger.debug("Injecting traceparent to event payload...")
            inject_traceparent(payload=payload)

        # Environment-specific handling
        if middleware_id:
            logger.debug("Custom middleware_id provided...")
            with _set_middleware_identifier(middleware_id):
                return _dispatch(event_name=event_name, payload=payload)
        else:
            return _dispatch(event_name=event_name, payload=payload)
