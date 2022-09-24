import logging
import os
from contextlib import contextmanager
from enum import Enum
from typing import Dict, Optional, Union

from fastapi_events import BaseEventHandler
from fastapi_events.constants import FASTAPI_EVENTS_USE_SPAN_LINKING_ENV_VAR
from fastapi_events.otel import HAS_OTEL_INSTALLED, propagate, trace
from fastapi_events.otel.attributes import SpanAttributes
from fastapi_events.utils import strtobool

logger = logging.getLogger(__name__)

USE_SPAN_LINKING_DEFAULT_VALUE = strtobool(os.environ.get(FASTAPI_EVENTS_USE_SPAN_LINKING_ENV_VAR, "1"))


@contextmanager
def empty_span():
    """
    A stub when OTEL is disabled or context (traceparent) cannot be extracted
    """
    yield


def create_span_for_handle_fn(
    handler_instance: BaseEventHandler,
    event_name: Union[str, Enum],
    payload: Optional[Dict] = None,
    use_span_linking: bool = USE_SPAN_LINKING_DEFAULT_VALUE
):
    if not HAS_OTEL_INSTALLED:
        logger.debug("Unable to create span. OTEL is not installed.")
        return empty_span()

    if payload is None:
        logger.debug("Unable to create span for event %s without payload.", event_name)
        return empty_span()

    links, context = [], None

    # Extract span from remote context
    remote_ctx = propagate.extract(payload)
    if use_span_linking:
        # while using span-linking mode, the remote span context should become a link
        context = None
        if remote_ctx:
            for item in remote_ctx.values():
                if hasattr(item, "get_span_context"):
                    links.append(trace.Link(context=item.get_span_context()))
    else:
        # while span-linking is not used, new spans created below should use
        # the remote span context as parent, and link the current span context
        # Get context from current span
        context = remote_ctx
        current_span = trace.get_current_span()
        links.append(trace.Link(context=current_span.get_span_context()))

    handler_module = handler_instance.__class__.__module__
    handler_name = handler_instance.__class__.__name__
    tracer = trace.get_tracer(handler_module)

    return tracer.start_as_current_span(f"handling event {event_name} with {handler_name}",
                                        context=context,
                                        links=links,
                                        kind=trace.SpanKind.CONSUMER,
                                        attributes={SpanAttributes.HANDLER: f"{handler_module}.{handler_name}"})


def create_span_for_dispatch_fn(
    event_name: Union[str, Enum],
):
    if not HAS_OTEL_INSTALLED:
        logger.debug("Unable to create span. OTEL is not installed.")
        return empty_span()

    tracer = trace.get_tracer("fastapi_events.dispatcher")

    return tracer.start_as_current_span(f"Event {event_name} dispatched",
                                        kind=trace.SpanKind.PRODUCER)


def inject_traceparent(payload: Dict):
    if not HAS_OTEL_INSTALLED:
        logger.debug("Unable to inject traceparent. OTEL is not installed.")
        return

    if not isinstance(payload, dict):
        logger.debug("Unable to inject traceparent. Payload is not a dict")
        return

    propagate.inject(payload)
