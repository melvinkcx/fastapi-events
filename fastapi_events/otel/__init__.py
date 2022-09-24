# flake8: noqa
try:
    from opentelemetry import trace, propagate  # type: ignore

    HAS_OTEL_INSTALLED = True
except ImportError:
    HAS_OTEL_INSTALLED = False
