from os import environ

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from testcontainers.google.pubsub import PubSubContainer

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.gcp import GoogleCloudPubSubHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware


def test_gcp_pubsub_handler():

    topic_id = "gcp-topic-id"
    project_id = "gcp-project-id"
    subscription_id = "gcp-topic-subscription-id"

    pubsub = PubSubContainer(image="google/cloud-sdk:latest", project=project_id)

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

    with pubsub:

        # google cloud pubsub client first looks for pubsub
        # emulator host if present instead of real
        # google cloud pubsub server
        environ["PUBSUB_EMULATOR_HOST"] = pubsub.get_pubsub_emulator_host()

        pub_client = pubsub.get_publisher_client()
        sub_client = pubsub.get_subscriber_client()

        topic_path = pub_client.topic_path(project_id, topic_id)
        subscription_path = sub_client.subscription_path(project_id, subscription_id)

        # create test topic
        pub_client.create_topic(name=topic_path)

        # create test subscription for the test topic
        sub_client.create_subscription(name=subscription_path, topic=topic_path)

        client = TestClient(setup_app())
        client.get("/")

        response = sub_client.pull(subscription=subscription_path, max_messages=100)
        assert len(response.received_messages) == 50
