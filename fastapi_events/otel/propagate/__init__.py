from fastapi_events.otel import HAS_OTEL_INSTALLED

if HAS_OTEL_INSTALLED:
    from opentelemetry import propagate  # type: ignore

    extract = propagate.extract
    inject = propagate.inject

else:
    from fastapi_events.otel.propagate import dummy

    extract = dummy.extract
    inject = dummy.inject
