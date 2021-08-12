from typing import Deque, Any, Optional

from fastapi_events import event_store
from fastapi_events.typing import Event


def dispatch(event_name: str, payload: Optional[Any] = None) -> None:
    q: Deque[Event] = event_store.get()
    q.append((event_name, payload))
