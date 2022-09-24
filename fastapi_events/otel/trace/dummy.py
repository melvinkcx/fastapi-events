from contextlib import contextmanager
from enum import Enum


class SpanKind(Enum):
    INTERNAL = 0
    SERVER = 1
    CLIENT = 2
    PRODUCER = 3
    CONSUMER = 4


class Tracer:
    """
    Partial interface of `opentelemetry.trace.Tracer`
    TODO make this a singleton
    """

    @contextmanager
    def start_span(self, *args, **kwargs):
        yield Span()

    @contextmanager
    def start_as_current_span(self, *args, **kwargs):
        yield Span()


class Span:
    """
    Partial interface of `opentelemetry.trace.Span`
    TODO make this a singleton
    """
    pass
