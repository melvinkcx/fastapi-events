from unittest.mock import Mock, patch

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.gcp import GoogleCloudPubSubHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware


@patch("google.cloud.pubsub_v1.PublisherClient")
def test_gcp_pubsub_handler(mock_publisher_client: Mock):

    topic_id = "gcp-topic-id"
    project_id = "gcp-project-id"

    def setup_app():
        app = Starlette(
            middleware=[
                Middleware(
                    EventHandlerASGIMiddleware,
                    handlers=[
                        GoogleCloudPubSubHandler(
                            project_id=project_id, topic_id=topic_id
                        )
                    ],
                )
            ]
        )

        @app.route("/")
        async def root(request: Request) -> JSONResponse:
            for idx in range(50):
                dispatch(event_name="event", payload={"idx": idx + 1})
            return JSONResponse([])

        return app

    app = setup_app()
    client = TestClient(app)
    client.get("/")

    assert mock_publisher_client.return_value.publish.call_count == 50
