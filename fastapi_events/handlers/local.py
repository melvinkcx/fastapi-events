import asyncio
import fnmatch
import functools
import inspect
import sys
from typing import Any, Callable, Dict, ForwardRef, List, Optional, Tuple, cast

# TODO Try to completely eliminate the need of using dependent libs
from fastapi import params  # FIXME
from pydantic.error_wrappers import ErrorWrapper

from fastapi_events.handlers.base import BaseEventHandler
from fastapi_events.otel.utils import create_span_for_handle_fn
from fastapi_events.typing import Event


def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
    """
    Adopted from pydantic source code
    """
    if sys.version_info < (3, 9):
        return type_._evaluate(globalns, localns)
    else:
        # Even though it is the right signature for python 3.9, mypy complains with
        # `error: Too many arguments for "_evaluate" of "ForwardRef"` hence the cast...
        return cast(Any, type_)._evaluate(globalns, localns, set())


def get_typed_annotation(
    annotation: Any,
    globalns: Dict[str, Any]
) -> Any:
    """
    Adopted from fastapi source code
    """
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_typed_signature(
    call: Callable[..., Any]
) -> inspect.Signature:
    """
    Adopted from fastapi source code
    """
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param.annotation, globalns),
        )
        for param in signature.parameters.values()
    ]
    typed_signature = inspect.Signature(typed_params)
    return typed_signature


class Dependant:
    def __init__(
        self,
        call: Callable[..., Any],
        name: Optional[str],
        dependencies: Optional[List["Dependant"]] = None,
    ):
        self.call = call
        self.name = name
        self.dependencies = dependencies or []


def get_param_sub_dependant(
    *,
    param: inspect.Parameter,
    name: str,
) -> Dependant:
    depends: params.Depends = param.default
    if depends.dependency:
        dependency = depends.dependency
    else:
        dependency = param.annotation

    return get_dependant(
        name=name,
        call=dependency,
    )


def get_dependant(
    *,
    call: Callable[..., Any],
    name: Optional[str] = None,
) -> Dependant:
    handler_signature = get_typed_signature(call)
    signature_params = handler_signature.parameters

    dependant = Dependant(
        call=call,
        name=name,
    )

    for param_name, param in signature_params.items():
        if isinstance(param.default, params.Depends):  # FIXME create a Protocol for params.Depends?
            sub_dependant = get_param_sub_dependant(
                param=param,
                name=param_name,
            )
            dependant.dependencies.append(sub_dependant)
            continue

    return dependant


async def solve_dependencies(
    *,
    event: Event,
    dependant: Dependant,
) -> Tuple[
    Dict[str, Any],
    List[ErrorWrapper]
]:
    values: Dict[str, Any] = {}
    errors: List[ErrorWrapper] = []

    for sub_dependant in dependant.dependencies:
        use_sub_dependant = sub_dependant
        call = sub_dependant.call

        sub_values, sub_errors = await solve_dependencies(
            event=event,
            dependant=use_sub_dependant,
        )
        if sub_errors:
            errors.extend(sub_errors)
            continue

        # TODO support dependencies with `yield`

        elif asyncio.iscoroutinefunction(call):
            solved = await call(**sub_values)
        else:
            loop = asyncio.get_event_loop()
            solved = await loop.run_in_executor(None, functools.partial(call, event, **sub_values))

        if sub_dependant.name is not None:
            values[sub_dependant.name] = solved

    return values, errors


class LocalHandler(BaseEventHandler):
    def __init__(self):
        self._registry = {}

    def register(self, _func=None, event_name="*"):
        def _wrap(func):
            self._register_handler(event_name, func)
            return func

        if _func is None:
            return _wrap

        return _wrap(func=_func)

    async def handle(self, event: Event) -> None:
        event_name, payload = event

        with create_span_for_handle_fn(
            handler_instance=self,
            event_name=event_name,
            payload=payload,
        ):
            for handler in self._get_handlers_for_event(event_name=event_name):
                # #41 resolve dependencies
                dependant = get_dependant(call=handler)
                values, errors = await solve_dependencies(event=event, dependant=dependant)

                if inspect.iscoroutinefunction(handler):
                    await handler(event, **values)
                else:
                    # Making sure sync function will never block the event loop
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, functools.partial(handler, event))

    def _register_handler(self, event_name, func):
        if not isinstance(event_name, str):
            event_name = str(event_name)

        if event_name not in self._registry:
            self._registry[event_name] = []

        self._registry[event_name].append(func)

    def _get_handlers_for_event(self, event_name):
        if not isinstance(event_name, str):
            event_name = str(event_name)

        # TODO consider adding a cache
        handlers = []
        for event_name_pattern, registered_handlers in self._registry.items():
            if fnmatch.fnmatch(event_name, event_name_pattern):
                handlers.extend(registered_handlers)

        return handlers


local_handler = LocalHandler()
