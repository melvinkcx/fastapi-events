from enum import Enum
from typing import Any, Awaitable, Callable, MutableMapping, Tuple, Union

Event = Tuple[Union[str, Enum], Any]
Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
