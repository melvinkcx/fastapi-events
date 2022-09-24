import pytest
from opentelemetry.test.test_base import TestBase as OTELTestManager


@pytest.fixture
def otel_test_manager():
    manager = OTELTestManager()
    manager.setUp()

    yield manager

    manager.tearDown()
