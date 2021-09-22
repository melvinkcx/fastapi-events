import abc
import asyncio
from abc import ABC
from typing import Iterable

from fastapi_events.typing import Event


class BaseEventHandler(ABC):
    async def handle_many(self, events: Iterable[Event]) -> None:
        await asyncio.gather(*[self.handle(event) for event in events])

    @abc.abstractmethod
    async def handle(self, event: Event) -> None:
        raise NotImplementedError
