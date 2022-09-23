from fastapi_events.otel import HAS_OTEL_INSTALLED

try:
    from opentelemetry import propagate  # type: ignore
except ImportError:
    from fastapi_events.otel.propagate import dummy

if HAS_OTEL_INSTALLED:
    extract = propagate.extract
    inject = propagate.inject
else:
    extract = dummy.extract
    inject = dummy.inject
