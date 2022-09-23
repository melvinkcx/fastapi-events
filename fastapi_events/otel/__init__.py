try:
    from opentelemetry import trace  # type: ignore

    HAS_OTEL_INSTALLED = True
except ImportError:
    HAS_OTEL_INSTALLED = False
