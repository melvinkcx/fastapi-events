try:
    from opentelemetry import trace
    from opentelemetry.trace import *

    HAS_OTEL_INSTALLED = True
except ImportError:
    from fastapi_events.otel.trace.dummy import *

    HAS_OTEL_INSTALLED = False


def get_tracer(*args, **kwargs):
    if HAS_OTEL_INSTALLED:
        return trace.get_tracer(*args, **kwargs)
    else:
        return DummyTracer()
