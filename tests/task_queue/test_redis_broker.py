import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
import fakeredis.aioredis

from katana.task_queue.models import Task, TaskStatus
from katana.task_queue.redis_broker import RedisBroker

# --- Test Setup ---

# Note for developers:
# These tests use `fakeredis` to mock a Redis instance in memory.
# No external Redis server is required to run these tests.


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    res._close = res.close
    res.close = lambda: None
    yield res
    res._close()


@pytest_asyncio.fixture(scope="function")
async def broker() -> RedisBroker:
    """
    Provides a RedisBroker instance for each test function, using a mocked
    in-memory Redis server (`fakeredis`).
    """
    # Instantiate the broker, it won't be able to connect to a real redis
    # but we are replacing the client right after.
    broker = RedisBroker(redis_url="redis://localhost:6379/0")

    # Create a fake redis client and replace the real one on the broker instance
    fake_redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    broker.redis = fake_redis_client

    yield broker

    # Clean up the fake redis server
    await fake_redis_client.flushall()
    # Close the connection
    await broker.close()


# --- Broker Tests ---


@pytest.mark.asyncio
async def test_broker_connection(broker: RedisBroker):
    """Test if the broker can connect to the mocked Redis."""
    assert await broker.redis.ping() is True


@pytest.mark.asyncio
async def test_broker_enqueue_dequeue_simple(broker: RedisBroker):
    """Test basic enqueue and dequeue of a single task that is due immediately."""
    task_id = uuid.uuid4()
    task = Task(
        id=task_id,
        priority=0,
        scheduled_at=datetime.now(timezone.utc),
        name="simple_task",
    )

    await broker.enqueue(task)

    dequeued = await broker.dequeue()
    assert dequeued is not None
    assert dequeued.id == task_id
    assert dequeued.name == "simple_task"

    # The queue should be empty now
    assert await broker.dequeue() is None


@pytest.mark.asyncio
async def test_broker_priority_order(broker: RedisBroker):
    """Test that tasks with higher priority (lower number) are dequeued first."""
    now = datetime.now(timezone.utc)
    task_low_prio = Task(priority=5, scheduled_at=now, name="low_prio")
    task_high_prio = Task(priority=0, scheduled_at=now, name="high_prio")

    await broker.enqueue(task_low_prio)
    await broker.enqueue(task_high_prio)

    dequeued1 = await broker.dequeue()
    assert dequeued1 is not None
    assert dequeued1.name == "high_prio"

    dequeued2 = await broker.dequeue()
    assert dequeued2 is not None
    assert dequeued2.name == "low_prio"


@pytest.mark.asyncio
async def test_broker_scheduled_at_order(broker: RedisBroker):
    """Test that a task scheduled for the future is not dequeued immediately."""
    now = datetime.now(timezone.utc)
    task_future = Task(
        priority=0, scheduled_at=now + timedelta(seconds=60), name="future_task"
    )
    task_now = Task(priority=5, scheduled_at=now, name="now_task")

    await broker.enqueue(task_future)
    await broker.enqueue(task_now)

    # Only the "now_task" should be dequeued, despite having lower priority
    dequeued1 = await broker.dequeue()
    assert dequeued1 is not None
    assert dequeued1.name == "now_task"

    # The future task should not be available yet
    assert await broker.dequeue() is None


@pytest.mark.asyncio
async def test_broker_dequeue_moves_scheduled_tasks(broker: RedisBroker):
    """Test that dequeue moves tasks from scheduled to due queue when they become ready."""
    now = datetime.now(timezone.utc)
    delay_seconds = 0.2
    task_delayed = Task(
        priority=1,
        scheduled_at=now + timedelta(seconds=delay_seconds),
        name="delayed_task",
    )

    await broker.enqueue(task_delayed)

    # Immediately, it should not be in the due queue
    assert await broker.dequeue() is None

    # Wait for the task to become due
    await asyncio.sleep(delay_seconds + 0.1)

    # Now it should be dequeued
    dequeued = await broker.dequeue()
    assert dequeued is not None
    assert dequeued.name == "delayed_task"


@pytest.mark.asyncio
async def test_get_task_and_task_exists(broker: RedisBroker):
    """Test retrieving a task by ID and checking for its existence."""
    task = Task(
        priority=0, scheduled_at=datetime.now(timezone.utc), name="get_task_test"
    )

    # Check existence before adding
    assert await broker.task_exists(task.id) is False

    await broker.enqueue(task)

    # Check existence after adding
    assert await broker.task_exists(task.id) is True

    # Retrieve the task
    retrieved_task = await broker.get_task(task.id)
    assert retrieved_task is not None
    assert retrieved_task.id == task.id
    assert retrieved_task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_broker_update_status(broker: RedisBroker):
    """Test updating the status of a task."""
    task = Task(
        priority=0, scheduled_at=datetime.now(timezone.utc), name="status_update_task"
    )
    await broker.enqueue(task)

    retrieved_before = await broker.get_task(task.id)
    assert retrieved_before.status == TaskStatus.PENDING

    # Mark as complete
    await broker.mark_complete(task.id)
    retrieved_after = await broker.get_task(task.id)
    assert retrieved_after.status == TaskStatus.COMPLETED

    # Mark as failed
    await broker.mark_failed(task.id)
    retrieved_failed = await broker.get_task(task.id)
    assert retrieved_failed.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_dequeue_empty_queues(broker: RedisBroker):
    """Test that dequeue returns None when both queues are empty."""
    assert await broker.dequeue() is None


@pytest.mark.asyncio
async def test_multiple_tasks_with_same_priority(broker: RedisBroker):
    """Test that tasks with the same priority are returned (order not guaranteed by this test)."""
    now = datetime.now(timezone.utc)
    task1 = Task(priority=1, scheduled_at=now, name="task1")
    task2 = Task(priority=1, scheduled_at=now, name="task2")

    await broker.enqueue(task1)
    await broker.enqueue(task2)

    dequeued1 = await broker.dequeue()
    dequeued2 = await broker.dequeue()

    assert dequeued1 is not None
    assert dequeued2 is not None

    # Verify we got both tasks, regardless of order
    dequeued_names = {dequeued1.name, dequeued2.name}
    assert dequeued_names == {"task1", "task2"}
