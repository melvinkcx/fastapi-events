import boto3

try:
    from moto import mock_sqs as mock_aws  # moto<=4
except ImportError:
    from moto import mock_aws  # moto>=5

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from fastapi_events.dispatcher import dispatch
from fastapi_events.handlers.aws import SQSForwardHandler
from fastapi_events.middleware import EventHandlerASGIMiddleware


@mock_aws
def test_aws_sqs_handler():
    def setup_app():
        app = Starlette(middleware=[
            Middleware(EventHandlerASGIMiddleware,
                       handlers=[SQSForwardHandler(queue_url="test-queue",
                                                   region_name="eu-central-1")])
        ])

        @app.route("/")
        async def root(request: Request) -> JSONResponse:
            for idx in range(50):
                dispatch(event_name="new event", payload={"id": idx + 1})

            return JSONResponse([])

        return app

    sqs = boto3.client("sqs", region_name="eu-central-1")
    queue = sqs.create_queue(QueueName="test-queue")

    app = setup_app()
    client = TestClient(app)
    client.get("/")

    for _ in range(5):
        messages = sqs.receive_message(QueueUrl=queue["QueueUrl"], MaxNumberOfMessages=10)["Messages"]
        assert len(messages) == 10
