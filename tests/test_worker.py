import pytest
import pytest_asyncio
from unittest.mock import patch
import asyncio

import fakeredis.aioredis
import worker

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to override environment variables for tests."""
    monkeypatch.setenv("REDIS_QUEUE_NAME", "worker_test_queue")

@pytest_asyncio.fixture
async def fake_redis():
    """Fixture to create a fake Redis instance for tests."""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()

@patch('worker.logger')
async def test_worker_processes_tasks(mock_worker_logger, mock_settings, fake_redis):
    """
    Tests that the worker correctly processes tasks from a pre-populated queue
    and shuts down gracefully with an event.
    """
    # Arrange
    tasks_to_process = ["worker test task 1", "worker test task 2"]
    queue_name = "worker_test_queue" # From mock_settings
    shutdown_event = asyncio.Event()

    # Pre-populate the fake Redis queue
    for task in tasks_to_process:
        await fake_redis.rpush(queue_name, task)

    assert await fake_redis.llen(queue_name) == len(tasks_to_process)

    # Patch the worker's redis connection and run it as a background task
    worker_task = None
    with patch('redis.asyncio.from_url', return_value=fake_redis):
        worker_task = asyncio.create_task(worker.main(shutdown_event=shutdown_event))

        # Wait for the worker to process all tasks
        for _ in range(10): # Timeout after 5 seconds
            if await fake_redis.llen(queue_name) == 0:
                break
            await asyncio.sleep(0.5)
        else:
            pytest.fail("Worker did not process all tasks in time.")

        # Signal the worker to shut down and wait for it
        try:
            shutdown_event.set()
            await asyncio.wait_for(worker_task, timeout=5)
        except asyncio.TimeoutError:
            pytest.fail("Worker did not shut down gracefully.")

    # Assert
    # Check that the queue is now empty
    assert await fake_redis.llen(queue_name) == 0

    # Verify the logs
    log_calls = mock_worker_logger.info.call_args_list
    log_messages = [call[0][0] for call in log_calls]

    assert any(f"Pulled task from queue '{queue_name}': {tasks_to_process[0]}" in msg for msg in log_messages)
    assert any(f"✅ Task completed: {tasks_to_process[0]}" in msg for msg in log_messages)
    assert any(f"Pulled task from queue '{queue_name}': {tasks_to_process[1]}" in msg for msg in log_messages)
    assert any(f"✅ Task completed: {tasks_to_process[1]}" in msg for msg in log_messages)
    assert any("Katana Worker has stopped." in msg for msg in log_messages)
