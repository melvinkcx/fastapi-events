# flake8: noqa
try:
    from opentelemetry import propagate, trace  # type: ignore

    HAS_OTEL_INSTALLED = True
except ImportError:
    HAS_OTEL_INSTALLED = False
