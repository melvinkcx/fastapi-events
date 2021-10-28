import os
from distutils.util import strtobool
from typing import Deque, Any, Optional

from fastapi_events import event_store
from fastapi_events.typing import Event


def dispatch(event_name: str, payload: Optional[Any] = None) -> None:
    DISABLE_DISPATCH_GLOBALLY = strtobool(os.environ.get("FASTAPI_EVENTS_DISABLE_DISPATCH", "0"))

    if DISABLE_DISPATCH_GLOBALLY:
        return

    q: Deque[Event] = event_store.get()
    q.append((event_name, payload))
