from typing import Any, Dict, Callable

from aio_pika import connect, Message, DeliveryMode

from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.serializers import json_serializer
from fastapi_events.typing import Event


class RabbitMQPubSubHandler(BaseEventHandler):
    def __init__(
        self,
        connection_params: Dict[str, Any],
        exchange_params: Dict[str, Any],
        serializer: Callable[[Event], str] = None,
    ):
        self._connection_params = connection_params
        self._exchange_params = exchange_params
        self._serializer = serializer or json_serializer

    async def _initialize(self):
        self._connection = await connect(**self._connection_params)
        self._channel = await self._connection.channel()
        self._exchange = self._channel.declare_exchange(**self._exchange_params)

    async def handle(self, event: Event) -> None:
        if not self._exchange:
            await self._initialize()

        msg = Message(body=self.format_message(event=event).encode(),
                      delivery_mode=DeliveryMode.PERSISTENT)
        await self._exchange.publish(message=msg, routing_key="info")
        await self._connection.close()

    def format_message(self, event: Event) -> str:
        return self._serializer(event)
