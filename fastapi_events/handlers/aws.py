import uuid
from typing import Iterable, Callable, Optional

import boto3 as boto3

from fastapi_events.errors import ConfigurationError
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event
from fastapi_events.utils import chunk


class SQSForwardHandler(BaseEventHandler):
    """
    AWS SQS Forward Handler
    - forwards all events to an SQS queue
    """

    def __init__(
        self,
        queue_url: str,
        region_name: str,
        serializer: Callable[[Event], str],
        max_batch_size: Optional[int] = 10  # AWS supports up to 10 messages at once
    ):
        if not callable(serializer):
            raise ConfigurationError("serializer must be a Callable")

        self._queue_url = queue_url
        self._region_name = region_name
        self._max_batch_size = max_batch_size

        self._client = boto3.client('sqs', region_name=self._region_name)
        self._serializer = serializer

    async def handle_many(self, events: Iterable[Event]) -> None:
        for batch in chunk(events, self._max_batch_size):
            self._client.send_message_batch(QueueUrl=self._queue_url,
                                            Entries=[{"Id": self.generate_id(event),
                                                      "MessageBody": self.format_message(event=event)}
                                                     for event in batch])

    async def handle(self, event: Event) -> None:
        self._client.send_message(QueueUrl=self._queue_url,
                                  DelaySeconds=0,
                                  MessageBody=self.format_message(event=event))

    def format_message(self, event: Event) -> str:
        return self._serializer(event)

    def generate_id(self, event: Event) -> str:
        return str(uuid.uuid4())
