import os

import pytest

import fastapi_events.dispatcher as dispatcher_module
from fastapi_events.dispatcher import dispatch


@pytest.mark.parametrize("suppress_events", [True, False])
def test_suppressing_of_events(
    suppress_events, mocker,
):
    """
    Test if dispatch() can be disabled properly with
    `FASTAPI_EVENTS_DISABLE_DISPATCH` environment variable.

    It should be enabled by default.
    """
    if suppress_events:
        mocker.patch.dict(os.environ, {"FASTAPI_EVENTS_DISABLE_DISPATCH": "1"})

    spy_event_store_ctx_var = mocker.spy(dispatcher_module, "event_store")

    dispatch("TEST_EVENT")

    assert spy_event_store_ctx_var.get.called != suppress_events
