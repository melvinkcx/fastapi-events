import json
from typing import Any, Callable, Dict, Iterable, Optional

from google.cloud import pubsub_v1

from fastapi_events.errors import ConfigurationError
from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


def _json_serializer(event: Event) -> str:
    return json.dumps(event, default=str)


class GoogleCloudSimplePubSubHandler(BaseEventHandler):
    def __init__(
        self,
        project_id: str,
        topic_id: str,
        max_batch_size: int = 1000,  # GCP Pubsub's maximum supported batch size
        batch_settings_kwargs: Optional[Dict[str, Any]] = None,
        serializer: Optional[Callable[[Event], str]] = None,
    ) -> None:
        """Google cloud simple PubSub handler. Publishes events to a single topic."""

        if max_batch_size > 1000:
            raise ConfigurationError("GCP Pubsub batch size limit is 1000.")

        if serializer is not None and not callable(serializer):
            raise ConfigurationError("serializer must be of type Callable")

        self._max_batch_size = max_batch_size

        # Publish messages as soon as there are max_messages
        # or 1 second is passed
        self._batch_settings = pubsub_v1.types.BatchSettings(
            max_messages=self._max_batch_size, **batch_settings_kwargs
        )
        self._client = pubsub_v1.PublisherClient(self._batch_settings)
        self._serializer = serializer or _json_serializer
        self._topic_path = self._client.topic_path(project_id, topic_id)

    async def handle_many(self, events: Iterable[Event]) -> None:
        for event in events:
            await self.handle(event)

    async def handle(self, event: Event) -> None:
        self._client.publish(self._topic_path, self.format_message(event))

    def format_message(self, event: Event) -> bytes:
        return self._serializer(event).encode("utf-8")
