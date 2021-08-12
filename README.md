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
    - Updates:
        - giving up using it, Middleware and BackgroundTasks dont work well together:
            - https://github.com/encode/starlette/issues/919
    - use a middleware (BaseHTTPMiddleware) to inject a function to `request.state` serve as a dispatcher/emitter
        - the middleware should inject/add a BackgroundTask (`response.background.add_task()`) to invoke the handlers
    - BaseHTTPMiddleware should NOT be used with StreamingResponse and FileResponse:
        -> Memory issues: https://github.com/encode/starlette/issues/1012#issuecomment-673461832
        -> https://github.com/encode/starlette/issues/919#issuecomment-672908610
    - Ref:
        - https://fastapi.tiangolo.com/tutorial/background-tasks/#dependency-injection
        - https://spectrum.chat/ariadne/general/how-to-use-background-tasks-with-starlette~74d56970-5676-4484-8586-a9384e5f4d56?m=MTU5MDc4NjIwMDMxOA==
        - https://github.com/austincollinpena/Starlette-Ariadne-Gino-Starter/blob/master/backend/main.py
    
    2. Use ASGIMiddleware:
    - Ref:
        - https://github.com/tomwojcik/starlette-context/blob/master/starlette_context/middleware/raw_middleware.py