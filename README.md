# fastapi-events

An event dispatching/handling library for FastAPI, and Starlette.

[![](https://github.com/melvinkcx/fastapi-events/actions/workflows/tests.yml/badge.svg?branch=dev&event=push)](https://github.com/melvinkcx/fastapi-events/actions/workflows/tests.yml)

Features:

* straightforward API to emit events anywhere in your code
* events are handled after responses are returned (doesn't affect response time)
* support event piping to remote queues
* powerful built-in handlers to handle events locally and remotely
* coroutine functions (`async def`) are the first-class citizen
* write your handlers, never be limited to just what `fastapi_events` provides

## Installation

```shell
pip install fastapi-events
```

To use it with AWS handlers, install:

```shell
pip install fastapi-events[aws]
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

## Handling Events

### Handle events locally

The flexibility of `fastapi-events` allows us to customise how the events should be handled. 
For starters, you might want to handle your events locally.

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

# Creating your own handler

Creating your own handler is nothing more than inheriting from the `BaseEventHandler` class in `fastapi_events.handlers.base`.

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

# Feedback, Questions?

Any form of feedback and questions are welcome! Please create an issue [here](https://github.com/melvinkcx/fastapi-events/issues/new).