import asyncio
import time
import uuid
import pytest
from unittest.mock import Mock, call

# Adjust import path if necessary based on your project structure
from katana.core.task_queue import TaskQueue, Task

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_hooks():
    return {
        "on_task_received": Mock(),
        "on_task_done": Mock(),
        "on_task_error": Mock(),
    }

@pytest.fixture
def task_queue(mock_hooks):
    return TaskQueue(**mock_hooks)

async def test_add_and_get_task(task_queue: TaskQueue, mock_hooks):
    """Test basic adding and getting a task."""
    task_data = {"key": "value"}
    task_id = await task_queue.add_task(task_data, priority=1)

    assert isinstance(task_id, uuid.UUID)
    mock_hooks["on_task_received"].assert_called_once()
    received_task_arg = mock_hooks["on_task_received"].call_args[0][0]
    assert isinstance(received_task_arg, Task)
    assert received_task_arg.task_id == task_id
    assert received_task_arg.data == task_data
    assert received_task_arg.priority == 1

    retrieved_task = await task_queue.get_task(timeout=0.1)
    assert retrieved_task is not None
    assert retrieved_task.task_id == task_id
    assert retrieved_task.data == task_data
    assert retrieved_task.priority == 1

async def test_get_task_timeout(task_queue: TaskQueue):
    """Test get_task timeout when queue is empty."""
    retrieved_task = await task_queue.get_task(timeout=0.01)
    assert retrieved_task is None

async def test_task_priority(task_queue: TaskQueue, mock_hooks):
    """Test that tasks are retrieved based on priority."""
    data_low_prio = "low_priority_task"
    data_high_prio = "high_priority_task"
    data_mid_prio = "mid_priority_task"

    await task_queue.add_task(data_low_prio, priority=10)
    await task_queue.add_task(data_high_prio, priority=0)
    await task_queue.add_task(data_mid_prio, priority=5)

    # Check hooks called for each task added
    assert mock_hooks["on_task_received"].call_count == 3

    task1 = await task_queue.get_task(timeout=0.1)
    assert task1 is not None
    assert task1.data == data_high_prio
    assert task1.priority == 0

    task2 = await task_queue.get_task(timeout=0.1)
    assert task2 is not None
    assert task2.data == data_mid_prio
    assert task2.priority == 5

    task3 = await task_queue.get_task(timeout=0.1)
    assert task3 is not None
    assert task3.data == data_low_prio
    assert task3.priority == 10

async def test_delayed_task(task_queue: TaskQueue, mock_hooks):
    """Test that delayed tasks are not available until the delay has passed."""
    task_data = "delayed_task"
    delay_seconds = 0.2

    await task_queue.add_task(task_data, priority=0, delay=delay_seconds)

    # Task should not be available immediately
    assert task_queue.qsize() == 0 # The task is not yet in the main PriorityQueue

    # on_task_received is called *after* the delay and put
    mock_hooks["on_task_received"].assert_not_called()

    # Wait for less than the delay time
    retrieved_task_too_soon = await task_queue.get_task(timeout=0.05)
    assert retrieved_task_too_soon is None

    # Wait for the delay to pass
    await asyncio.sleep(delay_seconds + 0.1) # Add a small buffer

    mock_hooks["on_task_received"].assert_called_once() # Now it should have been called
    received_task_arg = mock_hooks["on_task_received"].call_args[0][0]
    assert received_task_arg.data == task_data

    assert task_queue.qsize() == 1 # Task should now be in the queue
    retrieved_task_after_delay = await task_queue.get_task(timeout=0.1)
    assert retrieved_task_after_delay is not None
    assert retrieved_task_after_delay.data == task_data

async def test_acknowledge_task_and_hook(task_queue: TaskQueue, mock_hooks):
    """Test acknowledging a task and the on_task_done hook."""
    task_data = "task_to_acknowledge"
    task_id = await task_queue.add_task(task_data, priority=0)

    retrieved_task = await task_queue.get_task(timeout=0.1)
    assert retrieved_task is not None
    assert retrieved_task.task_id == task_id

    task_queue.acknowledge_task(retrieved_task.task_id)
    mock_hooks["on_task_done"].assert_called_once_with(retrieved_task.task_id)

async def test_report_task_error_and_hook(task_queue: TaskQueue, mock_hooks):
    """Test reporting a task error and the on_task_error hook."""
    task_data = "task_that_will_error"
    task_id = await task_queue.add_task(task_data, priority=0)

    retrieved_task = await task_queue.get_task(timeout=0.1)
    assert retrieved_task is not None
    assert retrieved_task.task_id == task_id

    error = ValueError("Processing failed")
    task_queue.report_task_error(retrieved_task.task_id, error)
    mock_hooks["on_task_error"].assert_called_once_with(retrieved_task.task_id, error)

async def test_queue_join_empty(task_queue: TaskQueue):
    """Test that join() returns immediately for an empty queue."""
    await task_queue.join() # Should not block

async def test_queue_join_with_tasks(task_queue: TaskQueue):
    """Test that join() waits for tasks to be processed."""
    task_data1 = "join_task1"
    task_data2 = "join_task2"

    await task_queue.add_task(task_data1)
    await task_queue.add_task(task_data2)

    join_task_completed = False

    async def process_tasks():
        nonlocal join_task_completed
        task1 = await task_queue.get_task(timeout=0.1)
        assert task1 is not None
        task_queue.acknowledge_task(task1.task_id)

        task2 = await task_queue.get_task(timeout=0.1)
        assert task2 is not None
        task_queue.acknowledge_task(task2.task_id)

        # This check is slightly indirect for join itself but ensures processing happened
        join_task_completed = True


    # Run process_tasks and join concurrently
    processing_coro = process_tasks()
    join_coro = task_queue.join()

    # Schedule them. If join() is correct, it should finish after processing_coro signals completion of tasks
    await asyncio.gather(processing_coro, join_coro)
    assert join_task_completed, "Tasks were not processed before join returned"
    assert task_queue.empty()

async def test_task_ordering_same_priority_fifo(task_queue: TaskQueue):
    """Test FIFO behavior for tasks with the same priority (relies on timestamp)."""
    task_data1 = "task1_same_prio"
    task_id1 = await task_queue.add_task(task_data1, priority=1)
    await asyncio.sleep(0.01) # ensure timestamp is different
    task_data2 = "task2_same_prio"
    task_id2 = await task_queue.add_task(task_data2, priority=1)
    await asyncio.sleep(0.01)
    task_data3 = "task3_same_prio"
    task_id3 = await task_queue.add_task(task_data3, priority=1)

    retrieved1 = await task_queue.get_task(timeout=0.1)
    assert retrieved1 is not None
    assert retrieved1.task_id == task_id1

    retrieved2 = await task_queue.get_task(timeout=0.1)
    assert retrieved2 is not None
    assert retrieved2.task_id == task_id2

    retrieved3 = await task_queue.get_task(timeout=0.1)
    assert retrieved3 is not None
    assert retrieved3.task_id == task_id3

async def test_hooks_robustness(mock_hooks):
    """Test that queue operations don't fail if a hook raises an exception."""

    def failing_received_hook(task):
        raise ValueError("Failed received hook")
    def failing_done_hook(task_id):
        raise ValueError("Failed done hook")
    def failing_error_hook(task_id, exc):
        raise ValueError("Failed error hook")

    # Intentionally cause print output, suppress if it's too noisy for test runs
    # For now, we just check that the queue doesn't crash.
    # In a real test suite, you might want to capture stdout/stderr.

    q_fail_hooks = TaskQueue(
        on_task_received=failing_received_hook,
        on_task_done=failing_done_hook,
        on_task_error=failing_error_hook
    )

    # Test on_task_received failure
    task_id1 = await q_fail_hooks.add_task("data1") # Should not raise here
    assert q_fail_hooks.qsize() == 1

    # Test on_task_done failure
    task1 = await q_fail_hooks.get_task()
    assert task1 is not None
    q_fail_hooks.acknowledge_task(task1.task_id) # Should not raise here

    # Test on_task_error failure
    task_id2 = await q_fail_hooks.add_task("data2")
    task2 = await q_fail_hooks.get_task()
    assert task2 is not None
    q_fail_hooks.report_task_error(task2.task_id, Exception("test error")) # Should not raise here
    # We still need to call task_done for join() if we were using it
    q_fail_hooks._queue.task_done()


    # Test delayed task with failing hook
    task_id3 = await q_fail_hooks.add_task("data3_delayed", delay=0.01)
    await asyncio.sleep(0.05) # allow delay to pass and hook to be called
    assert q_fail_hooks.qsize() == 1 # Should still be 1 (data3_delayed)
    task3 = await q_fail_hooks.get_task()
    assert task3 is not None
    q_fail_hooks.acknowledge_task(task3.task_id) # Should not raise

    # Ensure the queue is empty at the end
    assert q_fail_hooks.empty()

# It's good practice to ensure __init__.py exists in the tests directory
# (though pytest might not strictly require it for discovery depending on version/config)
# This step will be handled by "Create __init__.py files"
