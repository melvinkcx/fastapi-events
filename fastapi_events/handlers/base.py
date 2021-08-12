import abc
from abc import ABC
from typing import Iterable

from fastapi_events.typing import Event


class BaseEventHandler(ABC):
    @abc.abstractmethod
    async def handle_many(self, events: Iterable[Event]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def handle(self, event: Event) -> None:
        raise NotImplementedError
