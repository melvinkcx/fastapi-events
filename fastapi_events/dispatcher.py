from typing import Deque

from fastapi_events import event_store


def dispatch(event_name: str) -> None:
    q: Deque = event_store.get()
    q.append({"name": event_name, "payload": {}})
