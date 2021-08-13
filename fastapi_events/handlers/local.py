import functools


class LocalHandler:
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

    def _register_handler(self, event_name, func):
        if event_name not in self._registry:
            self._registry[event_name] = []

        self._registry[event_name].append(func)


local_handler = LocalHandler()
