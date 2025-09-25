import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict

import pytest

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from katana.task_queue.models import Task, TaskStatus
from katana.task_queue.broker import InMemoryBroker, AbstractBroker
from katana.task_queue.service import TaskQueueService, TaskExecutor


# --- Test Task Model ---
@pytest.mark.asyncio
async def test_task_creation_defaults():
    now = datetime.now(timezone.utc)
    task = Task(priority=1, scheduled_at=now, name="test_task")
    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.payload == {}
    assert task.created_at.replace(microsecond=0) == now.replace(
        microsecond=0
    )

@pytest.mark.asyncio
async def test_task_with_status():
    now = datetime.now(timezone.utc)
    task = Task(priority=1, scheduled_at=now, name="test_status_task")
    processing_task = task.with_status(TaskStatus.PROCESSING)
    assert processing_task.status == TaskStatus.PROCESSING
    assert processing_task.id == task.id
    assert processing_task.name == task.name


# --- Test InMemoryBroker ---
@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()


@pytest.mark.asyncio
async def test_broker_enqueue_dequeue_simple(broker: InMemoryBroker):
    task_id = uuid.uuid4()
    task = Task(
        id=task_id,
        priority=0,
        scheduled_at=datetime.now(timezone.utc),
        name="simple_task",
    )
    await broker.enqueue(task)
    assert await broker.get_queue_size() == 1

    dequeued = await broker.dequeue()
    assert dequeued is not None
    assert dequeued.id == task_id
    assert await broker.get_queue_size() == 0


@pytest.mark.asyncio
async def test_broker_priority_order(broker: InMemoryBroker):
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
async def test_broker_scheduled_at_order(broker: InMemoryBroker):
    now = datetime.now(timezone.utc)
    task_later = Task(
        priority=0, scheduled_at=now + timedelta(seconds=10), name="later_task"
    )
    task_now = Task(priority=0, scheduled_at=now, name="now_task")

    await broker.enqueue(task_later)
    await broker.enqueue(task_now)

    dequeued1 = await broker.dequeue()
    assert dequeued1 is not None
    assert dequeued1.name == "now_task"

    dequeued_none = await broker.dequeue()
    assert dequeued_none is None

    broker_new = InMemoryBroker()
    task_future = Task(
        priority=0,
        scheduled_at=datetime.now(timezone.utc) + timedelta(seconds=60),
        name="future_task",
    )
    await broker_new.enqueue(task_future)
    assert await broker_new.dequeue() is None


@pytest.mark.asyncio
async def test_broker_created_at_order(broker: InMemoryBroker):
    now = datetime.now(timezone.utc)
    task_first_created = Task(
        priority=0,
        scheduled_at=now,
        name="first_created",
        created_at=now - timedelta(seconds=1),
    )
    task_second_created = Task(
        priority=0, scheduled_at=now, name="second_created", created_at=now
    )

    await broker.enqueue(task_second_created)
    await broker.enqueue(task_first_created)

    dequeued1 = await broker.dequeue()
    assert dequeued1 is not None
    assert dequeued1.name == "first_created"

    dequeued2 = await broker.dequeue()
    assert dequeued2 is not None
    assert dequeued2.name == "second_created"


@pytest.mark.asyncio
async def test_broker_update_status(broker: InMemoryBroker):
    task = Task(
        priority=0, scheduled_at=datetime.now(timezone.utc), name="status_update_task"
    )
    await broker.enqueue(task)

    retrieved_before = await broker.get_task(task.id)
    assert retrieved_before is not None
    assert retrieved_before.status == TaskStatus.PENDING

    await broker.mark_complete(task.id)
    retrieved_after = await broker.get_task(task.id)
    assert retrieved_after is not None
    assert retrieved_after.status == TaskStatus.COMPLETED

    task_fail = Task(
        priority=0, scheduled_at=datetime.now(timezone.utc), name="fail_task"
    )
    await broker.enqueue(task_fail)
    await broker.mark_failed(task_fail.id)
    retrieved_failed = await broker.get_task(task_fail.id)
    assert retrieved_failed is not None
    assert retrieved_failed.status == TaskStatus.FAILED


# --- Test TaskQueueService ---

async def success_task_executor(payload):
    return "Success"

async def failure_task_executor():
    raise ValueError("Task failed as planned")


@pytest.fixture
def service(broker: InMemoryBroker) -> TaskQueueService:
    return TaskQueueService(broker=broker, task_executors={
        "success_task": success_task_executor,
        "failure_task": failure_task_executor,
    })


@pytest.mark.asyncio
async def test_service_worker_processes_task_successfully(
    service: TaskQueueService, broker: InMemoryBroker
):
    task_payload = {"key": "value"}

    added_task = await service.add_task_to_queue(success_task_executor, task_payload)
    logger.info(f"Test: Added task {added_task.id} for successful processing.")

    worker_task = asyncio.create_task(service.worker(worker_id=1, poll_interval=0.01))

    await asyncio.sleep(0.1)

    final_task_status = await broker.get_task(added_task.id)
    assert final_task_status is not None
    assert final_task_status.status == TaskStatus.COMPLETED
    assert final_task_status.result == "Success"

    service._stop_event.set()
    await asyncio.wait_for(worker_task, timeout=1.0)
    logger.info(f"Test: Worker task for successful processing completed.")


@pytest.mark.asyncio
async def test_service_worker_handles_task_failure(
    service: TaskQueueService, broker: InMemoryBroker
):
    added_task = await service.add_task_to_queue(failure_task_executor)
    logger.info(f"Test: Added task {added_task.id} for failure processing.")

    worker_task = asyncio.create_task(service.worker(worker_id=1, poll_interval=0.01))

    await asyncio.sleep(0.1)

    final_task_status = await broker.get_task(added_task.id)
    assert final_task_status is not None
    assert final_task_status.status == TaskStatus.FAILED

    service._stop_event.set()
    await asyncio.wait_for(worker_task, timeout=1.0)
    logger.info(f"Test: Worker task for failure processing completed.")


def simple_sync_task(a, b):
    return a + b

async def simple_async_task(a, b):
    await asyncio.sleep(0.01)
    return a * b

@pytest.mark.asyncio
@pytest.mark.parametrize("task_func, args, expected_result", [
    (simple_sync_task, (2, 3), 5),
    (simple_async_task, (3, 4), 12),
])
async def test_service_add_task_to_queue_pickled(
    service: TaskQueueService, broker: InMemoryBroker, task_func, args, expected_result
):
    added_task = await service.add_task_to_queue(task_func, *args)

    worker_task = asyncio.create_task(service.worker(worker_id=1, poll_interval=0.01))

    await asyncio.sleep(0.2)

    final_task_status = await broker.get_task(added_task.id)
    assert final_task_status is not None
    assert final_task_status.status == TaskStatus.COMPLETED
    assert final_task_status.result == expected_result

    service._stop_event.set()
    await asyncio.wait_for(worker_task, timeout=1.0)