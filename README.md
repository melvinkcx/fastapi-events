# fastapi-events

An event dispatching/handling library for FastAPI, and Starlette.

[![](https://github.com/melvinkcx/fastapi-events/actions/workflows/tests.yml/badge.svg?branch=dev&event=push)](https://github.com/melvinkcx/fastapi-events/actions/workflows/tests.yml)
![PyPI - Downloads](https://img.shields.io/pypi/dw/fastapi-events)

Features:

* straightforward API to emit events anywhere in your code
* events are handled after responses are returned (doesn't affect response time)
* supports event piping to remote queues
* powerful built-in handlers to handle events locally and remotely
* coroutine functions (`async def`) are the first-class citizen
* write your handlers, never be limited to just what `fastapi_events` provides
* (__>=0.3.0__) supports event payload validation via Pydantic (See [here](#event-payload-validation-with-pydantic))
* (__>=0.4.0__) supports event chaining: dispatching events within handlers (thank [@ndopj](https://github.com/ndopj)
  for contributing to the idea)
* (__>=0.7.0__) supports OpenTelemetry: see [this section](#opentelemetry-otel-support) for details
* (__>=0.9.0__) supports dependencies in local handlers: see [this section](#using-dependencies-in-local-handler) for details

If you use or like this project, please consider giving it a star so it can reach more developers. Thanks =)

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

Events can be dispatched anywhere in the code, as long as they are dispatched before a response is made.

```python
# anywhere in code

from fastapi_events.dispatcher import dispatch

dispatch(
    "cat-requested-a-fish",  # Event name, accepts any valid string
    payload={"cat_id": "fd375d23-b0c9-4271-a9e0-e028c4cd7230"}  # Event payload, accepts any arbitrary data
)

dispatch("a_cat_is_spotted")  # This works too!
```

### Event Payload Validation With Pydantic

Event payload validation is possible since version 0.3.0. To enable, simply register
a [Pydantic models](https://pydantic-docs.helpmanual.io/usage/models/) with the corresponding event name.

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
```

> Wildcard in event name is currently not supported

Payload will be validated automatically without any changes made while invoking the dispatcher.

```python
# Events with payload schema registered
dispatch(UserEvents.SIGNED_UP)  # raises ValidationError, missing payload
dispatch(UserEvents.SIGNED_UP,
         {"user_id": "9e79cdbb-b216-40f7-9a05-20d223dee89a"})  # raises ValidationError, missing `created_at`
dispatch(UserEvents.SIGNED_UP,
         {"user_id": "9e79cdbb-b216-40f7-9a05-20d223dee89a", created_at: datetime.utcnow()})  # OK!

# Events without payload schema -> No validation will be performed
dispatch(UserEvents.ACTIVATED,
         {"user_id": "9e79cdbb-b216-40f7-9a05-20d223dee89a"})  # OK! no validation will be performed
```

> Reminder: payload validation is optional.
> Payload of events without its schema registered will not be validated.

## Handling Events

### Handle events locally

The flexibility of `fastapi-events` allows us to customise how the events should be handled. For starters, you might
want to handle your events locally.

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

Dependencies can now be used with local handler. Sub-dependencies are also supported.

However, dependencies using generator (with `yield` keyword) is not supported yet. I have the intention to support it in the future.


```python
# ex: in handlers.py
from fastapi import Depends

from fastapi_events.handlers.local import local_handler
from fastapi_events.typing import Event

async def get_db_conn():
    pass    # return a DB conn


async def get_db_session(
    db_conn=Depends(get_db_conn)
):
    pass    # return a DB session created from `db_conn`



@local_handler.register(event_name="*")
async def handle_all_events(
    event: Event, 
    db_session=Depends(get_db_session)
):
    # use the `db_session` here
    pass
```

### Piping Events To Remote Queues

For larger projects, you might have services dedicated to handling events separately.

For instance, `fastapi-events` comes with AWS SQS forwarder to forward events to a remote queue.

1. Register `SQSForwardHandler` as handlers:
    ```python
    app = FastAPI()
    app.add_middleware(EventHandlerASGIMiddleware, 
                       handlers=[SQSForwardHandler(queue_url="test-queue",
                                                   region_name="eu-central-1")])   # registering handler(s)
    ```

2. Start dispatching events! Events will be serialised into JSON format by default:
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

# Creating your own handler

Creating your own handler is nothing more than inheriting from the `BaseEventHandler` class
in `fastapi_events.handlers.base`.

To handle events, `fastapi_events` calls one of these methods, in the following priority order:

1. `handle_many(events)`:
   The coroutine function should expect the backlog of the events collected.

2. `handle(event)`:
   In cases where `handle_many()` weren't defined in your custom handler, `handle()`
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

To enable it, make sure you install the optional modules:

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

In case you want to suppress events globally especially during testing, you can do so without having to mock or patch
the `dispatch()` function. Simple set the environment variable `FASTAPI_EVENTS_DISABLE_DISPATCH` to `1`, `True` or any
truthy values.

## 2) Validating Event Payload During Dispatch

> Requires Pydantic, which comes with FastAPI.
> If you're using Starlette, you might need to install Pydantic

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

One goal of `fastapi-events` is to dispatch events without having to manage which instance
of `EventHandlerASGIMiddleware` is being targeted. By default, this is handled using `ContextVars`. There are occasions
when a user may want to dispatch events outside of the standard request sequence though. This can be accomplished by
generating a custom identifier for the middleware.

By default, the middleware identifier is generated from the object id of the `EventHandlerASGIMiddleware` instance and
is managed internally without need for user intervention. If the user needs to dispatch events outside of a
request-response lifecycle, a custom `middleware_id` value can be generated and passed to `EventHandlerASGIMiddleware`
during its creation. This value can then be used with `dispatch()` to ensure the correct `EventHandlerASGIMiddleware`
instance is selected.

Dispatching events during a request does ***not*** require the `middleware_id`. These will continue to automatically
discover the event handler.

In the following example, the id is being generated using the object id of the `FastAPI` instance. The middleware
identifier must be unique `int` but there are no other restrictions.

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

   `dispatch()` relies on [ContextVars](https://docs.python.org/3/library/contextvars.html) to work properly. There are
   many reasons why `LookupError` can occur. A common reason is `dispatch()` is called outside the request-response
   lifecycle of FastAPI/Starlette, such as calling `dispatch()` after a response has been returned.

   [This can be worked around by using a user-defined middleware_id.](#4-dispatching-events-outside-of-a-request)

   If you're getting this during testing, you may consider disabling `dispatch()` during testing.
   See [Suppressing Events / Disabling `dispatch()` Globally](#suppressing-events--disabling-dispatch-globally) for
   details.

2. My event handlers are not registered / Local handlers are not being executed:

   Answer:

   Make sure the module where your local event handlers are defined is loaded during runtime. A simple fix is to import
   the module in your `__init__.py`. This will ensure the modules are properly loaded during runtime.

# Feedback, Questions?

Any form of feedback and questions are welcome! Please create an
issue [here](https://github.com/melvinkcx/fastapi-events/issues/new).