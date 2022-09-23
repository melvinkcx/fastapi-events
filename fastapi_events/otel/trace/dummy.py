from contextlib import contextmanager
from enum import Enum


class SpanKind(Enum):
    INTERNAL = 0
    SERVER = 1
    CLIENT = 2
    PRODUCER = 3
    CONSUMER = 4


class DummyTracer:
    @contextmanager
    def start_span(self, *args, **kwargs):
        yield

    @contextmanager
    def start_as_current_span(self, *args, **kwargs):
        yield
