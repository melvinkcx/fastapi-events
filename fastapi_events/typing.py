from enum import Enum
from typing import Any, Awaitable, Callable, MutableMapping, Tuple, Union

EventName = Union[str, Enum]
Event = Tuple[EventName, Any]
PydanticModel = Any  # FIXME
Payload = Union[dict, PydanticModel]
Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
