import boto3 as boto3

from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


class SQSForwardHandler(BaseEventHandler):
    """
    AWS SQS Forward Handler
    - forwards all events to an SQS queue
    """

    def __init__(self, queue_url: str, region_name: str):
        self._queue_url = queue_url
        self._region_name = region_name

        self._client = boto3.client('sqs', region_name=self._region_name)

    async def handle(self, event: Event) -> None:
        self._client.send_message(QueueUrl=self._queue_url,
                                  DelaySeconds=0,
                                  MessageBody=self.format_message(event=event))

    def format_message(self, event: Event) -> str:
        pass
