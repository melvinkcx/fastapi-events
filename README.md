# fastapi-events

## Installation

```python
from fastapi import FastAPI
from fastapi_events.middleware import EventHandlerMiddleware

app = FastAPI()
app.add_middleware(EventHandlerMiddleware)
```

# dev notes

- use a registry system
    - register events
    - register handler
- event structure?
    - ?
- how to store events?
- to run handlers in the background:
    1. Use BackgroundTask(s)

    - use a middleware to inject a function to `request.state` serve as a dispatcher/emitter
        - the middleware should inject/add a BackgroundTask (`response.background.add_task()`) to invoke the handlers
    - Ref:
        - https://fastapi.tiangolo.com/tutorial/background-tasks/#dependency-injection
        - https://spectrum.chat/ariadne/general/how-to-use-background-tasks-with-starlette~74d56970-5676-4484-8586-a9384e5f4d56?m=MTU5MDc4NjIwMDMxOA==
        - https://github.com/austincollinpena/Starlette-Ariadne-Gino-Starter/blob/master/backend/main.py