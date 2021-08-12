from pprint import pprint

from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


class EchoHandler(BaseEventHandler):
    """
    EchoHandler
    - forwards all events to stdout with `pprint`
    """
    async def handle(self, event: Event) -> None:
        pprint(event)
