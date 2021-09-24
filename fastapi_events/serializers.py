import json

from fastapi_events.typing import Event


def json_serializer(event: Event) -> str:
    return json.dumps(event, default=str)
