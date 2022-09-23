from fastapi_events.otel import HAS_OTEL_INSTALLED

try:
    from opentelemetry import trace  # type: ignore
except ImportError:
    from fastapi_events.otel.trace import dummy

if HAS_OTEL_INSTALLED:
    get_tracer = trace.get_tracer
else:
    get_tracer = dummy.Tracer()
