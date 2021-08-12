# fastapi-events

Event dispatching library for FastAPI, and Starlette.

Features:

* straightforward API to emit events in controllers
* handling of events will be done after responses are sent (doesn't affect response time)
* built-in and customizable event handlers; accept multiple handlers

## Installation

```shell
pip install fastapi-events
```

before using an AWS handler, install:

```shell
pip install fastapi-events[aws]
```

# Usage

`fastapi-events` despite its name, supports both FastAPI and Starlette.

* Configuring `fastapi-events` for FastAPI:
    ```python
    from fastapi import FastAPI
    from fastapi.requests import Request
    from fastapi.responses import JSONResponse
  
    from fastapi_events.dispatcher import dispatch
    from fastapi_events.middleware import EventHandlerASGIMiddleware
    from fastapi_events.handlers.echo import EchoHandler
    
    app = FastAPI()
    app.add_middleware(EventHandlerASGIMiddleware, handlers=[EchoHandler()])
    
    
    @app.get("/")
    def index(request: Request) -> JSONResponse:
        dispatch("my-fancy-event", payload={"id": 1})  # Emitting event in controllers
        return JSONResponse()    
    ```

* Configuring `fastapi-events` for Starlette:

  ```python
  from starlette.applications import Starlette
  from starlette.middleware import Middleware
  from starlette.requests import Request
  from starlette.responses import JSONResponse
  
  from fastapi_events.dispatcher import dispatch
  from fastapi_events.handlers.echo import EchoHandler
  from fastapi_events.middleware import EventHandlerASGIMiddleware
  
  app = Starlette(middleware=[
      Middleware(EventHandlerASGIMiddleware,
                 handlers=[EchoHandler()])
  ])
  
  @app.route("/")
  async def root(request: Request) -> JSONResponse:
      dispatch("new event", payload={"id": 1})
      return JSONResponse()
  ```

## Dispatching events

```python
from fastapi_events.dispatcher import dispatch

dispatch(
    "event-name",  # Event name, accepts any valid string
    payload={}  # Event payload, accepts any arbitrary data
)
```

# Built-in handlers

Here is a list of built-in event handlers

- `EchoHandler`: forward events to stdout (with `pprint`)
- `SQSForwardHandler`: forwards events to an AWS SQS queue

# Creating your own handler

TODO

# Design and Technical Details

TODO