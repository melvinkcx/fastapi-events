from typing import Iterable

from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


class NullHandler(BaseEventHandler):
    """
    NullHandler
    a handler that does nothing.
    can be used as a stub when a handler is expected.
    """
    async def handle(self, event: Event) -> None:
        ...

    async def handle_many(self, events: Iterable[Event]) -> None:
        ...
