import fnmatch
import functools
import inspect

from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.typing import Event


class LocalHandler(BaseEventHandler):
    def __init__(self):
        self._registry = {}

    def register(self, _func=None, event_name="*"):
        def _wrap(func):
            self._register_handler(event_name, func)

            @functools.wraps(func)
            def _wrapper(*args, **kwargs):
                return func(event_name, *args, **kwargs)

            return _wrapper

        if _func is None:
            return _wrap
        else:
            return _wrap(func=_func)

    async def handle(self, event: Event) -> None:
        for handler in self._get_handlers_for_event(event_name=event[0]):
            if inspect.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

    def _register_handler(self, event_name, func):
        if event_name not in self._registry:
            self._registry[event_name] = []

        self._registry[event_name].append(func)

    def _get_handlers_for_event(self, event_name):
        # TODO consider adding a cache
        handlers = []
        for event_name_pattern, registered_handlers in self._registry.items():
            if fnmatch.fnmatch(event_name, event_name_pattern):
                handlers.extend(registered_handlers)

        return handlers


local_handler = LocalHandler()
