from fastapi_events.otel import HAS_OTEL_INSTALLED

if HAS_OTEL_INSTALLED:
    from opentelemetry import trace

    get_tracer = trace.get_tracer

else:
    from fastapi_events.otel.trace import dummy

    get_tracer = dummy.Tracer()  # type: ignore[assignment]
