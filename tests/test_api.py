import pytest
import pytest_asyncio
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
import fakeredis.aioredis

from main import app

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to override environment variables for tests."""
    monkeypatch.setenv("REDIS_QUEUE_NAME", "api_test_queue")

@pytest_asyncio.fixture
async def fake_redis():
    """Fixture to create a fake Redis instance for tests."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()

@pytest_asyncio.fixture
async def client(fake_redis, mock_settings):
    """
    Creates a TestClient with a mocked Redis connection in its lifespan.
    """
    # Mock the lifespan context manager to inject the fake_redis client
    @asynccontextmanager
    async def mock_lifespan(app_instance):
        app_instance.state.redis = fake_redis
        yield

    app.router.lifespan_context = mock_lifespan
    with TestClient(app) as test_client:
        yield test_client

async def test_webhook_queues_tasks(client, fake_redis):
    """
    Tests that the /n8n/webhook endpoint correctly queues tasks in Redis.
    """
    # Arrange
    tasks_to_send = ["api test task 1", "api test task 2"]
    payload = {"tasks": tasks_to_send}
    queue_name = "api_test_queue" # From mock_settings

    # Act
    response = client.post("/n8n/webhook", json=payload)

    # Assert
    assert response.status_code == 202
    assert response.json()["message"] == f"Successfully queued {len(tasks_to_send)} tasks."

    # Verify that the tasks are in the fake Redis queue
    assert await fake_redis.llen(queue_name) == len(tasks_to_send)
    queued_tasks = await fake_redis.lrange(queue_name, 0, -1)
    assert queued_tasks == tasks_to_send

async def test_webhook_empty_list(client, fake_redis):
    """
    Tests that the webhook handles an empty task list correctly.
    """
    # Arrange
    payload = {"tasks": []}
    queue_name = "api_test_queue"

    # Act
    response = client.post("/n8n/webhook", json=payload)

    # Assert
    assert response.status_code == 202
    assert response.json()["message"] == "Received empty task list. No action taken."
    assert await fake_redis.llen(queue_name) == 0
