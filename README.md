# fastapi-events

An event dispatching/handling library for FastAPI, and Starlette.

[![](https://github.com/melvinkcx/fastapi-events/actions/workflows/tests.yml/badge.svg?branch=dev&event=push)](https://github.com/melvinkcx/fastapi-events/actions/workflows/tests.yml)
![PyPI - Downloads](https://img.shields.io/pypi/dw/fastapi-events)

Features:

* Straightforward API for emitting events anywhere in your code.
* Events are handled after responses are returned, ensuring no impact on response time.
* Supports event piping to remote queues.
* Powerful built-in handlers for local and remote event handling
* Coroutine functions (`async def`) are treated as first-class citizens
* Write your own handlers; don't be limited to just what `fastapi_events` provides
* (__>=0.3.0__) Supports event payload validation via Pydantic (See [here](#event-payload-validation-with-pydantic))
* (__>=0.4.0__) Supports event chaining: dispatching events within handlers (thanks to [@ndopj](https://github.com/ndopj)
  for contributing to the idea)
* (__>=0.7.0__) Supports OpenTelemetry. See [this section](#opentelemetry-otel-support) for details
* (__>=0.9.0__) Adds support for [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) in local handlers. See [this section](#using-dependencies-in-local-handler) for
  details
* (__>=0.9.1__) Now supports Pydantic v2
* (__>=0.10.0__) Enables dispatching Pydantic models as events (thanks to [@WilliamStam](https://github.com/WilliamStam) for contributing to this idea)

If you use or appreciate this project, please consider giving it a star to help it reach more developers. Thanks =)

## Installation

```shell
pip install fastapi-events
```

To use it with AWS handlers, install:

```shell
pip install fastapi-events[aws]
```

To use it with GCP handlers. install:

```shell
pip install fastapi-events[google]
```

To enable OpenTelemetry (OTEL) support, install:

```shell
pip install fastapi-events[otel]
```

# Usage

`fastapi-events` supports both FastAPI and Starlette. To use it, simply configure it as middleware.

* Configuring `fastapi-events` for FastAPI:
    ```python
    from fastapi import FastAPI
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse
  
    from fastapi_events.dispatcher import dispatch
    from fastapi_events.middleware import EventHandlerASGIMiddleware
    from fastapi_events.handlers.local import local_handler

    
    app = FastAPI()
    app.add_middleware(EventHandlerASGIMiddleware, 
                       handlers=[local_handler])   # registering handler(s)
    
    
    @app.get("/")
    def index(request: Request) -> JSONResponse:
        dispatch("my-fancy-event", payload={"id": 1})  # Emit events anywhere in your code
        return JSONResponse()    
    ```

* Configuring `fastapi-events` for Starlette:

  ```python
  from starlette.applications import Starlette
  from starlette.middleware import Middleware
  from starlette.requests import Request
  from starlette.responses import JSONResponse
  
  from fastapi_events.dispatcher import dispatch
  from fastapi_events.handlers.local import local_handler
  from fastapi_events.middleware import EventHandlerASGIMiddleware
  
  app = Starlette(middleware=[
      Middleware(EventHandlerASGIMiddleware,
                 handlers=[local_handler])  # registering handlers
  ])
  
  @app.route("/")
  async def root(request: Request) -> JSONResponse:
      dispatch("new event", payload={"id": 1})   # Emit events anywhere in your code
      return JSONResponse()
  ```

* Configuring `fastapi-events` for Starlite:

  ```python
  from starlite.app import Starlite
  from starlite.enums import MediaType
  from starlite.handlers import get
  from starlite.middleware import DefineMiddleware
  
  from fastapi_events.dispatcher import dispatch
  from fastapi_events.handlers.local import local_handler
  from fastapi_events.middleware import EventHandlerASGIMiddleware
  
  @get(path="/", media_type=MediaType.TEXT)
  async def root() -> str:
      dispatch("new event", payload={"id": 1})   # Emit events anywhere in your code
      return "OK"

  app = Starlite(middleware=[
      DefineMiddleware(EventHandlerASGIMiddleware,
                 handlers=[local_handler])  # registering handlers
      ],
      route_handlers=[root],
    )

  ```

## Dispatching events

Events can be dispatched anywhere in the code, provided that they are dispatched before a response is generated.

### Option 1 - using dict

```python
# anywhere in code

from fastapi_events.dispatcher import dispatch

dispatch(
    "cat-requested-a-fish",  # Event name, accepts any valid string
    payload={"cat_id": "fd375d23-b0c9-4271-a9e0-e028c4cd7230"}  # Event payload, accepts any arbitrary data
)

dispatch("a_cat_is_spotted")  # This works too!
```

### Option 2 - using Pydantic model

> New feature since version 0.10.0

It is now possible to dispatch pydantic model as events. A special thanks to
[@WilliamStam](https://github.com/WilliamStam) for introducing this remarkable idea.

```python
# anywhere in code
import pydantic
from fastapi_events.dispatcher import dispatch


class CatRequestedAFishEvent(pydantic.BaseModel):
    __event_name__ = "cat-requested-a-fish"

    cat_id: pydantic.UUID4


# Option 2 - dispatching event with pydantic model
dispatch(CatRequestedAFishEvent(cat_id="fd375d23-b0c9-4271-a9e0-e028c4cd7230"))

# which is equivalent to:
dispatch("cat-requested-a-fish", payload={"cat_id": "fd375d23-b0c9-4271-a9e0-e028c4cd7230"})
```

## Event Payload Validation With Pydantic

Since version 0.3.0, event payload validation is possible. To enable this feature, register a Pydantic model with the corresponding event name.

> __>=0.10.0__: Event name can now be defined as a part of the payload schema as `__event_name__`
```python
import uuid
from enum import Enum
from datetime import datetime

from pydantic import BaseModel
from fastapi_events.registry.payload_schema import registry as payload_schema


class UserEvents(Enum):
    SIGNED_UP = "USER_SIGNED_UP"
    ACTIVATED = "USER_ACTIVATED"


# Registering your event payload schema
@payload_schema.register(event_name=UserEvents.SIGNED_UP)
class SignUpPayload(BaseModel):
    user_id: uuid.UUID
    created_at: datetime

# which is also equivalent to
@payload_schema.register
class SignUpPayload(BaseModel):
    __event_name__ = "USER_SIGNED_UP"
    
    user_id: uuid.UUID
    created_at: datetime
```

> Wildcard in event name is currently not supported

The payload will be validated automatically without any changes required when invoking the dispatcher.

```python
# Events with payload schema registered
dispatch(UserEvents.SIGNED_UP)  # raises ValidationError, missing payload
dispatch(UserEvents.SIGNED_UP,
         {"user_id": "9e79cdbb-b216-40f7-9a05-20d223dee89a"})  # raises ValidationError, missing `created_at`
dispatch(UserEvents.SIGNED_UP,
         {"user_id": "9e79cdbb-b216-40f7-9a05-20d223dee89a", "created_at": datetime.utcnow()})  # OK!

# Events without payload schema -> No validation will be performed
dispatch(UserEvents.ACTIVATED,
         {"user_id": "9e79cdbb-b216-40f7-9a05-20d223dee89a"})  # OK! no validation will be performed

# Events dispatched with Pydantic model (>=0.10.0) -> Validation will be skipped since it would have been already validated
# If you choose to do this, you must ensure __event_name__ is defined in SignUpPayload
dispatch(SignUpPayload(user_id="9e79cdbb-b216-40f7-9a05-20d223dee89a", created_at=datetime.utcnow()))
```

> Payload validation is optional. Payload of events without its schema registered will not be validated.

## Handling Events

### Handle events locally

The flexibility of `fastapi-events` enales customisation of how events should be handled. To begin, you may want to handle your events locally.

```python
# ex: in handlers.py

from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event


@local_handler.register(event_name="cat*")
def handle_all_cat_events(event: Event):
    """
    this handler will match with an events prefixed with `cat`.
    ex: "cat_eats_a_fish", "cat_is_cute", etc
    """
    # the `event` argument is nothing more than a tuple of event name and payload
    event_name, payload = event

    # TODO do anything you'd like with the event


@local_handler.register(event_name="cat*")  # Tip: You can register several handlers with the same event name
def handle_all_cat_events_another_way(event: Event):
    pass


@local_handler.register(event_name="*")
async def handle_all_events(event: Event):
    # event handlers can be coroutine function too (`async def`)
    pass
```

#### Using Dependencies in Local Handler

> new feature in fastapi-events>=0.9.0
> 
Dependencies can now be utilized with local handlers, and sub-dependencies are also supported.

As of now, dependencies utilizing a generator (with the `yield` keyword) are not yet supported.

```python
# ex: in handlers.py
from fastapi import Depends

from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event


async def get_db_conn():
    pass  # return a DB conn


async def get_db_session(
    db_conn=Depends(get_db_conn)
):
    pass  # return a DB session created from `db_conn`


@local_handler.register(event_name="*")
async def handle_all_events(
    event: Event,
    db_session=Depends(get_db_session)
):
    # use the `db_session` here
    pass
```

### Piping Events To Remote Queues

In larger projects, it's common to have dedicated services for handling events separately. 
For example, `fastapi-events` includes an AWS SQS forwarder, allowing you to forward events to a remote queue.

1. Register `SQSForwardHandler` as handlers:
    ```python
    app = FastAPI()
    app.add_middleware(EventHandlerASGIMiddleware, 
                       handlers=[SQSForwardHandler(queue_url="test-queue",
                                                   region_name="eu-central-1")])   # registering handler(s)
    ```

2. Start dispatching events! By default, events will be serialised into JSON format:
    ```python
    ["event name", {"payload": "here is the payload"}]
    ```

> Tip: to pipe events to multiple queues, provide multiple handlers while adding `EventHandlerASGIMiddleware`.

# Built-in handlers

Here is a list of built-in event handlers:

* `LocalHandler` / `local_handler`:
    * import from `fastapi_events.handlers.local`
    * for handling events locally. See examples [above](#handle-events-locally)
    * event name pattern matching is done using Unix shell-style matching (`fnmatch`)

* `SQSForwardHandler`:
    * import from `fastapi_events.handlers.aws`
    * to forward events to an AWS SQS queue

* `EchoHandler`:
    * import from `fastapi_events.handlers.echo`
    * to forward events to stdout with `pprint`. Great for debugging purpose

* `GoogleCloudSimplePubSubHandler`:
    * import from `fastapi_events.handlers.gcp`
    * to publish events to a single pubsub topic

# Creating Custom Handlers

Creating your own handler is as simple as inheriting from the `BaseEventHandler` class
in `fastapi_events.handlers.base`.

To handle events, `fastapi_events` calls one of these methods, following this priority order:

1. `handle_many(events)`:
   The coroutine function should expect the backlog of the events collected.

2. `handle(event)`:
   If `handle_many()` is not defined in your custom handler, `handle()`
   will be called by iterating through the events in the backlog.

```python
from typing import Iterable

from fastapi_events.typing import Event
from fastapi_events.handlers.base import BaseEventHandler


class MyOwnEventHandler(BaseEventHandler):
    async def handle(self, event: Event) -> None:
        """
        Handle events one by one
        """
        pass

    async def handle_many(self, events: Iterable[Event]) -> None:
        """
        Handle events by batch
        """
        pass
```

# OpenTelemetry (OTEL) support

Since version 0.7.0, OpenTelemetry support has been added as an optional feature.

To enable it, make sure you install the following optional modules:

```shell
pip install fastapi-events[otel]
```

> Note that no instrumentation library is needed as fastapi_events supports OTEL natively

Spans will be created when:

* `fastapi_events.dispatcher.dispatch` is invoked,
* `fastapi_events.handlers.local.LocalHandler` is handling an event

Support for other handlers will be added in the future.

# Cookbook

## 1) Suppressing Events / Disabling `dispatch()` Globally

If you wish to globally suppress events, especially during testing, you can achieve this without having to mock or patch the dispatch() function. 
Simply set the environment variable FASTAPI_EVENTS_DISABLE_DISPATCH to 1, True, or any truthy values.

## 2) Validating Event Payload During Dispatch

> This feature requires Pydantic, which is included with FastAPI.
> If you're using Starlette, ensure that Pydantic is installed separately.

See [Event Payload Validation With Pydantic](#event-payload-validation-with-pydantic)

## 3) Dispatching events within handlers (Event Chaining)

It is now possible to dispatch events within another event handlers. You'll need version 0.4 or above.

Comparison between events dispatched within the request-response cycle and event handlers are:

|                                                                 | dispatched within request-response cycle         | dispatched within event handlers                        |
|-----------------------------------------------------------------|--------------------------------------------------|---------------------------------------------------------|
| processing of events                                            | will be handled after the response has been made | will be scheduled to the running event loop immediately |
| order of processing                                             | always after the response is made                | not guaranteed                                          |
| supports payload schema validation with Pydantic                | Yes                                              | Yes                                                     |
| can be disabled globally with `FASTAPI_EVENTS_DISABLE_DISPATCH` | Yes                                              | Yes                                                     |

## 4) Dispatching events outside of a request

One of the goals of `fastapi-events` is to dispatch events without the need to manage specific instance of `EventHandlerASGIMiddleware`.
By default, this is handled using `ContextVars`. 
However, there are scenarios where users may want to dispatch events outside the standard request sequence. 
This can be achieved by generating a custom identifier for the middleware.

By default, the middleware identifier is generated from the object ID of the `EventHandlerASGIMiddleware` instance and is managed internally without user intervention. 
If a user needs to dispatch events outside of a request-response lifecycle, they can generate a custom `middleware_id` value and passed it to `EventHandlerASGIMiddleware` during its creation. 
This value can then be used with `dispatch()` to ensure the correct `EventHandlerASGIMiddleware` instance is selected.

It's important to note that dispatching events during a request does not require the middleware_id. 
The dispatcher will automatically discover the appropriate event handler.

In the following example, the ID is generated using the object ID of the `FastAPI` instance. 
The middleware identifier must be a unique `int`, but there are no other restrictions.

```python
import asyncio

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from fastapi_events.dispatcher import dispatch
from fastapi_events.middleware import EventHandlerASGIMiddleware
from fastapi_events.handlers.local import local_handler

app = FastAPI()
event_handler_id: int = id(app)
app.add_middleware(EventHandlerASGIMiddleware,
                   handlers=[local_handler],  # registering handler(s)
                   middleware_id=event_handler_id)  # register custom middleware id


async def dispatch_task() -> None:
    """ background task to dispatch autonomous events """

    for i in range(100):
        # without the middleware_id, this call would raise a LookupError
        dispatch("date", payload={"idx": i}, middleware_id=event_handler_id)
        await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event() -> None:
    asyncio.create_task(dispatch_task())


@app.get("/")
def index(request: Request) -> JSONResponse:
    dispatch("hello", payload={"id": 1})  # Emit events anywhere in your code
    return JSONResponse({"detail": {"msg": "hello world"}})
```

# FAQs:

1. I'm getting `LookupError` when `dispatch()` is used:
    ```bash
        def dispatch(event_name: str, payload: Optional[Any] = None) -> None:
    >       q: Deque[Event] = event_store.get()
    E       LookupError: <ContextVar name='fastapi_context' at 0x400a1f12b0>
    ```

   Answer:

   The proper functioning of `dispatch()` relies on [ContextVars](https://docs.python.org/3/library/contextvars.html). 
   Various factors can lead to a LookupError, with a common cause being the invocation of `dispatch()` outside the request-response lifecycle of FastAPI/Starlette, such as calling `dispatch()` after a response has been returned.

   If you encounter this issue, a workaround is available by using a user-defined middleware_id. 
   Refer to [Dispatching Events Outside of a Request](#4-dispatching-events-outside-of-a-request) for details.

   If you're encountering this during testing, consider disabling `dispatch()` for testing purposes.
   Refer to [Suppressing Events / Disabling `dispatch()` Globally](#suppressing-events--disabling-dispatch-globally) for
   details.

2. My event handlers are not registered / Local handlers are not being executed:

   Answer:

   To ensure that the module where your local event handlers are defined is loaded during runtime, make sure to import the module in your __init__.py. 
   This straightforward fix guarantees the proper loading of modules during runtime.

# Feedback, Questions?

Any form of feedback and questions are welcome! Please create an
issue [here](https://github.com/melvinkcx/fastapi-events/issues/new).