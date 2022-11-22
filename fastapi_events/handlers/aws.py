import json
import uuid
from typing import Callable, Iterable, Optional

import boto3

from fastapi_events.errors import ConfigurationError
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event
from fastapi_events.utils import chunk


def _uuid4_generator(_: Event) -> str:
    return str(uuid.uuid4())


def _json_serializer(event: Event) -> str:
    return json.dumps(event, default=str)


class SQSForwardHandler(BaseEventHandler):
    """
    AWS SQS Forward Handler
    - forwards all events to an SQS queue
    """

    def __init__(
        self,
        queue_url: str,
        region_name: str,
        serializer: Optional[Callable[[Event], str]] = None,
        id_generator: Optional[Callable[[Event], str]] = None,
        max_batch_size: int = 10,  # AWS supports up to 10 messages at once
        **boto_client_kwargs
    ):
        for fn in (serializer, id_generator):
            if fn is not None and not callable(fn):
                raise ConfigurationError("serializer and id_generator must be of type Callable")

        if max_batch_size > 10:
            raise ConfigurationError("SQS doesn't support batch size larger than 10")

        self._queue_url = queue_url
        self._region_name = region_name
        self._max_batch_size = max_batch_size

        self._client = boto3.client('sqs', region_name=self._region_name, **boto_client_kwargs)
        self._serializer = serializer or _json_serializer
        self._id_generator = id_generator or _uuid4_generator

    async def handle_many(self, events: Iterable[Event]) -> None:
        for batch in chunk(events, self._max_batch_size):
            messages = [{"Id": self.generate_id(event),
                         "MessageBody": self.format_message(event=event)}
                        for event in batch]
            self._client.send_message_batch(QueueUrl=self._queue_url,
                                            Entries=messages)

    async def handle(self, event: Event) -> None:
        self._client.send_message(QueueUrl=self._queue_url,
                                  MessageBody=self.format_message(event=event))

    def format_message(self, event: Event) -> str:
        return self._serializer(event)

    def generate_id(self, event: Event) -> str:
        return self._id_generator(event)
