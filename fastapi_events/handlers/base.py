import abc
from abc import ABC

from fastapi_events.typing import Event


class BaseEventHandler(ABC):
    @abc.abstractmethod
    async def handle(self, event: Event) -> None:
        raise NotImplementedError
