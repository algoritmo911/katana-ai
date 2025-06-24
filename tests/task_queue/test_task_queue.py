import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Setup basic logging for tests to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Assuming the katana module is in thePYTHONPATH or installed
# If running pytest from project root, imports should work like this:
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
    assert task.created_at.replace(microsecond=0) == now.replace(microsecond=0) # Approx check

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
    task = Task(id=task_id, priority=0, scheduled_at=datetime.now(timezone.utc), name="simple_task")
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
    task_later = Task(priority=0, scheduled_at=now + timedelta(seconds=10), name="later_task") # Not due
    task_now = Task(priority=0, scheduled_at=now, name="now_task") # Due

    await broker.enqueue(task_later)
    await broker.enqueue(task_now)

    # Dequeue now_task first
    dequeued1 = await broker.dequeue()
    assert dequeued1 is not None
    assert dequeued1.name == "now_task"

    # later_task is not due yet
    dequeued_none = await broker.dequeue()
    assert dequeued_none is None

    # Wait for later_task to be due
    await asyncio.sleep(0.01) # Short sleep, assuming test runs fast enough for this to be relevant if delay was tiny
                              # For actual delays, time needs to pass. The InMemoryBroker test in broker.py handles this.
                              # This test verifies that if a task *is* due, it's picked before a non-due one.
                              # Let's adjust the test for clarity on "due" status.

    # Re-test with explicit check for non-due task
    broker_new = InMemoryBroker() # Fresh broker
    task_future = Task(priority=0, scheduled_at=datetime.now(timezone.utc) + timedelta(seconds=60), name="future_task")
    await broker_new.enqueue(task_future)
    assert await broker_new.dequeue() is None, "Future task should not be dequeued"


@pytest.mark.asyncio
async def test_broker_created_at_order(broker: InMemoryBroker):
    # Test tie-breaking by creation time if priority and scheduled_at are same
    now = datetime.now(timezone.utc)
    task_first_created = Task(priority=0, scheduled_at=now, name="first_created", created_at=now - timedelta(seconds=1))
    task_second_created = Task(priority=0, scheduled_at=now, name="second_created", created_at=now)

    await broker.enqueue(task_second_created) # Enqueue out of order of creation
    await broker.enqueue(task_first_created)

    dequeued1 = await broker.dequeue()
    assert dequeued1 is not None
    assert dequeued1.name == "first_created"

    dequeued2 = await broker.dequeue()
    assert dequeued2 is not None
    assert dequeued2.name == "second_created"


@pytest.mark.asyncio
async def test_broker_update_status(broker: InMemoryBroker):
    task = Task(priority=0, scheduled_at=datetime.now(timezone.utc), name="status_update_task")
    await broker.enqueue(task)

    retrieved_before = await broker.get_task(task.id)
    assert retrieved_before is not None
    assert retrieved_before.status == TaskStatus.PENDING

    await broker.mark_complete(task.id)
    retrieved_after = await broker.get_task(task.id)
    assert retrieved_after is not None
    assert retrieved_after.status == TaskStatus.COMPLETED

    # Test mark_failed
    task_fail = Task(priority=0, scheduled_at=datetime.now(timezone.utc), name="fail_task")
    await broker.enqueue(task_fail)
    await broker.mark_failed(task_fail.id)
    retrieved_failed = await broker.get_task(task_fail.id)
    assert retrieved_failed is not None
    assert retrieved_failed.status == TaskStatus.FAILED


# --- Test TaskQueueService ---

# Mock executor functions for service tests
mock_executor_success = AsyncMock(return_value=None)
mock_executor_failure = AsyncMock(side_effect=ValueError("Task failed as planned"))

@pytest.fixture
def service_executors() -> Dict[str, TaskExecutor]:
    # Reset mocks for each test
    mock_executor_success.reset_mock()
    mock_executor_failure.reset_mock()
    return {
        "success_task": mock_executor_success,
        "failure_task": mock_executor_failure,
    }

@pytest.fixture
def service(broker: InMemoryBroker, service_executors: Dict[str, TaskExecutor]) -> TaskQueueService:
    return TaskQueueService(broker=broker, task_executors=service_executors)

@pytest.mark.asyncio
async def test_service_add_task(service: TaskQueueService, broker: InMemoryBroker):
    task_name = "success_task"
    payload = {"data": "test_payload"}

    created_task = await service.add_task(name=task_name, payload=payload, priority=1)

    assert created_task.name == task_name
    assert created_task.payload == payload
    assert created_task.priority == 1
    assert created_task.status == TaskStatus.PENDING

    # Check if it's in the broker
    retrieved_from_broker = await broker.get_task(created_task.id)
    assert retrieved_from_broker is not None
    assert retrieved_from_broker.id == created_task.id

@pytest.mark.asyncio
async def test_service_add_task_unknown_executor(service: TaskQueueService):
    with pytest.raises(ValueError, match="Task name 'unknown_task_type' not found"):
        await service.add_task(name="unknown_task_type", payload={})

@pytest.mark.asyncio
async def test_service_worker_processes_task_successfully(service: TaskQueueService, broker: InMemoryBroker):
    task_name = "success_task"
    task_payload = {"key": "value"}

    # Add a task
    added_task = await service.add_task(name=task_name, payload=task_payload)
    logger.info(f"Test: Added task {added_task.id} for successful processing.")

    # Start a worker in the background (or run it directly for one cycle in test)
    # We'll simulate a single worker run for predictability in test

    worker_task = asyncio.create_task(service.worker(worker_id=1, poll_interval=0.01))

    # Give the worker some time to pick up and process the task
    await asyncio.sleep(0.1) # Adjust as needed, depends on executor's simulated work time

    # Check if the mock executor was called
    mock_executor_success.assert_called_once()
    call_args = mock_executor_success.call_args[0][0] # Get the Task object passed to executor
    assert call_args.id == added_task.id
    assert call_args.payload == task_payload

    # Check task status in broker
    final_task_status = await broker.get_task(added_task.id)
    assert final_task_status is not None
    assert final_task_status.status == TaskStatus.COMPLETED

    # Shutdown the worker
    service._stop_event.set() # Signal worker to stop
    await asyncio.wait_for(worker_task, timeout=1.0) # Wait for worker to finish
    logger.info(f"Test: Worker task for successful processing completed.")


@pytest.mark.asyncio
async def test_service_worker_handles_task_failure(service: TaskQueueService, broker: InMemoryBroker):
    task_name = "failure_task"

    added_task = await service.add_task(name=task_name, payload={"attempt": 1})
    logger.info(f"Test: Added task {added_task.id} for failure processing.")

    worker_task = asyncio.create_task(service.worker(worker_id=1, poll_interval=0.01))

    await asyncio.sleep(0.1)

    mock_executor_failure.assert_called_once()

    final_task_status = await broker.get_task(added_task.id)
    assert final_task_status is not None
    assert final_task_status.status == TaskStatus.FAILED

    service._stop_event.set()
    await asyncio.wait_for(worker_task, timeout=1.0)
    logger.info(f"Test: Worker task for failure processing completed.")


@pytest.mark.asyncio
async def test_service_worker_handles_delayed_task(service: TaskQueueService, broker: InMemoryBroker):
    task_name = "success_task"
    delay = 0.2 # seconds

    logger.info(f"Test: Adding delayed task, delay={delay}s.")
    added_task = await service.add_task(name=task_name, payload={"delayed": True}, delay_seconds=delay)

    worker_task = asyncio.create_task(service.worker(worker_id=1, poll_interval=0.01))

    # Immediately after adding, executor should not have been called
    await asyncio.sleep(0.05) # Less than delay
    mock_executor_success.assert_not_called()

    task_status_before_due = await broker.get_task(added_task.id)
    assert task_status_before_due is not None
    assert task_status_before_due.status == TaskStatus.PENDING # Still pending

    logger.info(f"Test: Waiting for delayed task to become due (slept 0.05s, need {delay - 0.05}s more).")
    # Wait for the task to become due and be processed
    await asyncio.sleep(delay + 0.1) # Total time > delay + processing time + poll interval

    mock_executor_success.assert_called_once()
    final_task_status = await broker.get_task(added_task.id)
    assert final_task_status is not None
    assert final_task_status.status == TaskStatus.COMPLETED

    service._stop_event.set()
    await asyncio.wait_for(worker_task, timeout=1.0)
    logger.info(f"Test: Worker task for delayed processing completed.")

@pytest.mark.asyncio
async def test_service_multiple_workers_share_load(broker: InMemoryBroker, service_executors: Dict[str, TaskExecutor]):
    # Use a slightly modified executor that records which worker processed it
    # This is tricky to assert deterministically with real async workers.
    # A simpler check is that all tasks get processed.

    processed_tasks_count = 0
    processing_lock = asyncio.Lock()

    async def counting_executor(task: Task):
        nonlocal processed_tasks_count
        logger.info(f"CountingExecutor processing task {task.id} with payload {task.payload}")
        await asyncio.sleep(0.05) # Simulate work
        async with processing_lock:
            processed_tasks_count +=1

    execs = {"count_me": counting_executor}
    service_multi = TaskQueueService(broker=broker, task_executors=execs)

    num_tasks = 5
    for i in range(num_tasks):
        await service_multi.add_task(name="count_me", payload={"task_num": i})

    # Start multiple workers
    num_workers = 3
    worker_coroutines = [service_multi.worker(worker_id=i, poll_interval=0.01) for i in range(num_workers)]
    worker_async_tasks = [asyncio.create_task(coro) for coro in worker_coroutines]

    # Let them run until all tasks should be processed
    # Each task takes ~0.05s. With 3 workers, 5 tasks should take roughly (5/3)*0.05s + overhead
    # Let's give it a bit more time, e.g., 0.5 seconds
    await asyncio.sleep(0.5)

    assert processed_tasks_count == num_tasks, f"Expected {num_tasks} tasks to be processed, but got {processed_tasks_count}"

    # Shutdown
    service_multi._stop_event.set()
    await asyncio.gather(*worker_async_tasks, return_exceptions=True)
    logger.info("Test: Multi-worker load sharing test completed.")


@pytest.mark.asyncio
async def test_service_shutdown_stops_workers(service: TaskQueueService):
    # Start workers
    worker_tasks = service.start_workers(num_workers=2, poll_interval=0.01)
    await asyncio.sleep(0.05) # Let them start

    # Initiate shutdown
    await service.shutdown() # This sets the _stop_event

    # Wait for tasks to finish, they should stop polling and exit
    done, pending = await asyncio.wait(worker_tasks, timeout=1.0)

    assert len(pending) == 0, "Not all worker tasks finished after shutdown"
    assert len(done) == len(worker_tasks), "Mismatch in finished worker tasks"
    for task_in_done in done:
        assert task_in_done.done(), "Task in 'done' set is not actually done"
        if task_in_done.exception(): # Propagate exceptions if any for debugging
            raise task_in_done.exception()

    logger.info("Test: Service shutdown correctly stops workers.")

# Consider adding tests for:
# - Task with non-existent executor name (service._execute_task path)
# - Broker errors during service operations (e.g., enqueue fails - how service handles this)
# - Idempotency if task_id is provided to add_task (broker needs to handle this, e.g. ignore or update)
# - What happens if a task is marked COMPLETED/FAILED externally before a worker picks it up?
#   (The current worker logic re-fetches task state and should skip if not PENDING)

# To run these tests:
# Ensure pytest and pytest-asyncio are installed: pip install pytest pytest-asyncio
# Navigate to the root of your project and run: pytest
# Or: pytest tests/task_queue/test_task_queue.py
#
# If katana module is not found, you might need to set PYTHONPATH:
# export PYTHONPATH=. (from project root)
# Or install your package in editable mode: pip install -e .

# Example of a task that takes time, for manual observation if needed
# async def long_running_mock_executor(task: Task):
#     logger.info(f"Long runner START: {task.id}, payload: {task.payload}")
#     await asyncio.sleep(task.payload.get("duration", 2)) # Sleep for 2 seconds
#     logger.info(f"Long runner END: {task.id}")

# This test file provides a good suite for the current functionality.
# More complex scenarios (e.g., broker failures, network issues for a Redis broker)
# would require more sophisticated mocking or integration testing setups.

# A small helper to run specific async tests if not using pytest runner directly for debugging
# async def main():
#   broker_instance = InMemoryBroker()
#   executors_instance = { "success_task": mock_executor_success, "failure_task": mock_executor_failure }
#   service_instance = TaskQueueService(broker=broker_instance, task_executors=executors_instance)
#   await test_service_worker_handles_delayed_task(service_instance, broker_instance)

# if __name__ == "__main__":
#    asyncio.run(main())
