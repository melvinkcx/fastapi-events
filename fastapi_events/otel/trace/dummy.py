from contextlib import contextmanager
from enum import Enum
from typing import Iterator


class SpanKind(Enum):
    INTERNAL = 0
    SERVER = 1
    CLIENT = 2
    PRODUCER = 3
    CONSUMER = 4


class DummyTracer:
    """
    Partial interface of `opentelemetry.trace.Tracer`
    """

    @contextmanager
    def start_span(self, *args, **kwargs) -> "DummySpan":
        yield DummySpan()

    @contextmanager
    def start_as_current_span(self, *args, **kwargs) -> Iterator["DummySpan"]:
        yield DummySpan()


class DummySpan:
    """
    Partial interface of `opentelemetry.trace.Span`
    """

    def set_attributes(self, attributes) -> None:
        ...

    def set_attribute(self, key, value) -> None:
        ...
