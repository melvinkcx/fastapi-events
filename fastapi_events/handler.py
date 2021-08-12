from typing import Deque

from fastapi_events import event_store


def handle_events():
    q: Deque = event_store.get()
    for event in q:
        # TODO process events
        print(event)
