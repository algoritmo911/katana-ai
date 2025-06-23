import asyncio
import pytest
from unittest.mock import AsyncMock, patch, call # Using AsyncMock for async methods

# Adjust import path based on how pytest will discover your modules.
# If tests/ is at the same level as src/, and you run pytest from project root:
from src.orchestrator.task_orchestrator import TaskOrchestrator, TaskResult, Task
from src.agents.julius_agent import JuliusAgent # Needed for type hinting mock

# Pytest needs to be able to run async tests
pytestmark = pytest.mark.asyncio

# Default task properties for easier test setup
DEFAULT_PRIORITY = TaskOrchestrator.DEFAULT_PRIORITY
RETRY_PRIORITY = TaskOrchestrator.RETRY_PRIORITY
MAX_RETRIES = TaskOrchestrator.MAX_RETRIES

# --- Helper Functions / Fixtures ---

@pytest.fixture
def mock_julius_agent(mocker):
    """Fixture to create a mock JuliusAgent."""
    agent = mocker.MagicMock(spec=JuliusAgent) # Use MagicMock for the class itself
    agent.process_tasks = AsyncMock() # Specifically make process_tasks an AsyncMock
    return agent

@pytest.fixture
def orchestrator(mock_julius_agent):
    """Fixture to create a TaskOrchestrator instance with a mocked agent."""
    # Patching _initialize_metrics_log_file and _log_metric_to_file to prevent actual file I/O during tests
    with patch.object(TaskOrchestrator, '_initialize_metrics_log_file', return_value=None), \
         patch.object(TaskOrchestrator, '_log_metric_to_file', return_value=None) as mock_log_to_file:

        instance = TaskOrchestrator(agent=mock_julius_agent, batch_size=2, max_batch=5)
        instance.mock_log_to_file = mock_log_to_file # Attach mock for assertions if needed
        yield instance


# --- Test Cases ---

async def test_orchestrator_initialization(orchestrator, mock_julius_agent):
    assert orchestrator.agent == mock_julius_agent
    assert orchestrator.batch_size == 2
    assert orchestrator.max_batch == 5
    assert orchestrator.min_batch_size == 1
    assert len(orchestrator.task_queue) == 0
    assert len(orchestrator.metrics_history) == 0
    orchestrator._initialize_metrics_log_file.assert_called_once()


async def test_add_tasks(orchestrator):
    tasks_content = ["task1", "task2"]
    orchestrator.add_tasks(tasks_content)
    assert len(orchestrator.task_queue) == 2
    for i, task_content in enumerate(tasks_content):
        assert orchestrator.task_queue[i].content == task_content
        assert orchestrator.task_queue[i].retries == 0
        assert orchestrator.task_queue[i].priority == DEFAULT_PRIORITY

    orchestrator.add_tasks(["task3"])
    assert len(orchestrator.task_queue) == 3
    assert orchestrator.task_queue[2].content == "task3"
    # Tasks should be sorted by priority, then retries. All are default here.
    # If priorities were different, order might change.
    expected_order = [
        Task(content="task1", retries=0, priority=DEFAULT_PRIORITY),
        Task(content="task2", retries=0, priority=DEFAULT_PRIORITY),
        Task(content="task3", retries=0, priority=DEFAULT_PRIORITY)
    ]
    assert orchestrator.task_queue == expected_order


async def test_run_round_empty_queue(orchestrator, mock_julius_agent):
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_not_called()
    assert len(orchestrator.metrics_history) == 0
    orchestrator.mock_log_to_file.assert_not_called()


async def test_run_round_all_success_increase_batch_size(orchestrator, mock_julius_agent):
    tasks = ["task1", "task2", "task3"]
    orchestrator.add_tasks(["task1", "task2", "task3"]) # 3 tasks
    orchestrator.batch_size = 2 # Initial batch size for this test (from fixture)

    # Mock agent to return all success for the first batch
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2"])
    assert orchestrator.batch_size == 3 # Increased from 2
    assert len(orchestrator.task_queue) == 1
    assert orchestrator.task_queue[0].content == "task3" # task3 remaining
    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 2
    assert metric['failed_tasks_count'] == 0
    assert metric['avg_time_per_task_seconds'] >= 0
    assert metric['error_types_in_batch'] == {}
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_all_success_at_max_batch_size(orchestrator, mock_julius_agent):
    orchestrator.batch_size = orchestrator.max_batch # Start at max batch (5)
    orchestrator.add_tasks(["task1", "task2"])

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]
    await orchestrator.run_round()
    # Agent called with task contents
    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2"])
    assert orchestrator.batch_size == orchestrator.max_batch # Stays at max
    orchestrator.mock_log_to_file.assert_called_once()

async def test_run_round_multiple_failures_decrease_batch_size(orchestrator, mock_julius_agent):
    # orchestrator default batch_size is 2 (from fixture)
    orchestrator.add_tasks(["task1", "task2", "task3"])
    orchestrator.batch_size = 3 # Set higher for test, to process all 3 tasks initially

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail connection", task_content="task1"), # Will be retried
        TaskResult(success=False, details="Fail timeout", task_content="task2"), # Will be retried
        TaskResult(success=True, details="Success", task_content="task3"),
    ]

    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2", "task3"])
    assert orchestrator.batch_size == 2 # Decreased from 3 due to 2 failures

    assert len(orchestrator.task_queue) == 2 # task1 and task2 are requeued
    # Verify requeued tasks (order might depend on sorting, check presence and properties)
    requeued_contents = {t.content for t in orchestrator.task_queue}
    assert "task1" in requeued_contents
    assert "task2" in requeued_contents
    for task_in_queue in orchestrator.task_queue:
        if task_in_queue.content in ["task1", "task2"]:
            assert task_in_queue.retries == 1
            assert task_in_queue.priority == RETRY_PRIORITY

    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 1
    assert metric['failed_tasks_count'] == 2
    assert metric['error_types_in_batch'] == {"CONNECTION_ERROR": 1, "TIMEOUT_ERROR": 1}
    orchestrator.mock_log_to_file.assert_called_once()

async def test_run_round_multiple_failures_at_min_batch_size(orchestrator, mock_julius_agent):
    orchestrator.batch_size = orchestrator.min_batch_size # Start at min (1)
    orchestrator.add_tasks(["task1", "task2"]) # Add two tasks

    # First round processes 1 task (min_batch_size), it fails
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail", task_content="task1") # Will be retried
    ]
    await orchestrator.run_round() # Processes task1 (content)
    # Batch size should remain min_batch_size. The rule is: decrease if failed_tasks_count > 1.
    # Here, failed_tasks_count is 1, so batch size does not decrease.
    assert orchestrator.batch_size == orchestrator.min_batch_size
    assert mock_julius_agent.process_tasks.call_count == 1
    mock_julius_agent.process_tasks.assert_called_with(["task1"])
    assert len(orchestrator.task_queue) == 2 # task2 (original) and task1 (retried)
    assert Task(content="task1", retries=1, priority=RETRY_PRIORITY) in orchestrator.task_queue
    assert Task(content="task2", retries=0, priority=DEFAULT_PRIORITY) in orchestrator.task_queue


    # If we had a batch size of 2, and both failed:
    orchestrator.batch_size = 2
    orchestrator.task_queue.clear()
    orchestrator.add_tasks(["task_A", "task_B"])
    mock_julius_agent.process_tasks.reset_mock()
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail", task_content="task_A"), # Retry
        TaskResult(success=False, details="Fail", task_content="task_B"), # Retry
    ]
    await orchestrator.run_round()
    assert orchestrator.batch_size == 1 # Decreased to min_batch_size (2 -> 1)
    assert len(orchestrator.task_queue) == 2
    assert Task(content="task_A", retries=1, priority=RETRY_PRIORITY) in orchestrator.task_queue
    assert Task(content="task_B", retries=1, priority=RETRY_PRIORITY) in orchestrator.task_queue
    orchestrator.mock_log_to_file.assert_called() # Called twice now (once above, once here)


async def test_run_round_single_failure_no_batch_size_change_but_retry(orchestrator, mock_julius_agent):
    orchestrator.batch_size = 3 # Current batch size
    orchestrator.add_tasks(["task1", "task2", "task3"])
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=False, details="Fail general", task_content="task2"), # Will be retried
        TaskResult(success=True, details="Success", task_content="task3"),
    ]
    await orchestrator.run_round()
    # Batch size does not change for a single failure in a batch > 1
    # The logic is `self.batch_size -1 if failed_tasks_count > 1 else self.batch_size`
    # Since failed_tasks_count is 1, it stays the same.
    assert orchestrator.batch_size == 3
    assert len(orchestrator.task_queue) == 1 # task2 retried
    assert orchestrator.task_queue[0] == Task(content="task2", retries=1, priority=RETRY_PRIORITY)
    metric = orchestrator.metrics_history[0]
    assert metric['failed_tasks_count'] == 1
    assert metric['error_types_in_batch'] == {"GENERAL_FAILURE": 1}
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_processes_fewer_than_batch_size_if_queue_small(orchestrator, mock_julius_agent):
    # Fixture: batch_size=2, max_batch=5
    # orchestrator.batch_size = 5 # This overrides fixture for this test instance if needed
    orchestrator.add_tasks(["task1", "task2"]) # Only 2 tasks in queue, batch_size is 2 (from fixture)

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2"])
    assert len(orchestrator.task_queue) == 0
    assert orchestrator.batch_size == 3 # Increased from 2 (fixture) because all 2 tasks were successful

    # Resetting for clarity with fixture values (initial batch_size=2)
    orchestrator.batch_size = 2 # from fixture
    orchestrator.task_queue.clear()
    orchestrator.metrics_history.clear()
    mock_julius_agent.process_tasks.reset_mock()
    orchestrator.mock_log_to_file.reset_mock()

    orchestrator.add_tasks(["taskA"]) # Queue smaller than batch_size (1 task, batch_size=2)
    mock_julius_agent.process_tasks.return_value = [TaskResult(success=True, details="S", task_content="taskA")]

    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(["taskA"])
    assert orchestrator.batch_size == 3 # Increased because the single task was successful
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_metrics_collection(orchestrator, mock_julius_agent):
    orchestrator.add_tasks(["task1_content"]) # Use different name to avoid confusion
    mock_julius_agent.process_tasks.return_value = [TaskResult(success=True, details="S", task_content="task1_content")]

    await orchestrator.run_round()
    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    # Initial batch_size is 2 (from fixture). After 1 success, it becomes 3.
    # So, batch_size_at_round_start was 2.
    assert metric['batch_size_at_round_start'] == 2
    assert metric['tasks_processed_in_batch'] == 1
    assert metric['successful_tasks_count'] == 1
    assert metric['failed_tasks_count'] == 0
    assert metric['success_rate_in_batch'] == 1.0
    assert 'time_taken_seconds' in metric
    assert 'avg_time_per_task_seconds' in metric
    assert metric['error_types_in_batch'] == {}
    # 'batch_tasks_content_with_retry_info' was how I named it in my head, but the actual log is 'results_summary'
    assert len(metric['results_summary']) == 1
    rs = metric['results_summary'][0]
    assert rs['task_content'] == "task1_content"
    assert rs['success'] is True
    assert rs['retries_attempted'] == 0 # First attempt
    orchestrator.mock_log_to_file.assert_called_once_with(metric)


async def test_get_status_method(orchestrator, mock_julius_agent):
    orchestrator.add_tasks(["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10", "t11"]) # 11 tasks
    orchestrator.batch_size = 3 # Override fixture's default of 2 for this test

    results_template = TaskResult(success=True, details="S", task_content="")

    # Round 1: batch_size=3, 3 tasks (t1,t2,t3), all succeed. New batch_size=4. Queue: 8 left.
    mock_julius_agent.process_tasks.return_value = [results_template._replace(task_content=f"t{i+1}") for i in range(3)]
    await orchestrator.run_round()

    # Round 2: batch_size=4, 4 tasks (t4,t5,t6,t7), all succeed. New batch_size=5 (max). Queue: 4 left.
    mock_julius_agent.process_tasks.return_value = [results_template._replace(task_content=f"t{i+4}") for i in range(4)]
    await orchestrator.run_round()

    # Round 3: batch_size=5, 4 tasks (t8,t9,t10,t11), all succeed. New batch_size=5 (max). Queue: 0 left.
    mock_julius_agent.process_tasks.return_value = [results_template._replace(task_content=f"t{i+8}") for i in range(4)]
    await orchestrator.run_round()

    status = orchestrator.get_status()
    assert status['current_batch_size'] == 5 # Max batch size (as per fixture)
    assert status['task_queue_length'] == 0 # All tasks processed
    assert status['tasks_pending_retry'] == 0
    assert status['max_retries_per_task'] == MAX_RETRIES
    assert status['total_metrics_rounds'] == 3
    assert len(status['last_10_rounds_metrics']) == 3
    assert len(status['task_queue_preview']) == 0


    # Simulate more rounds to test "last_10_rounds_metrics"
    for i in range(10):
        # Add tasks for the current batch_size (which should be 5)
        task_contents = [f"extra_task_{i}_{j}" for j in range(status['current_batch_size'])]
        orchestrator.add_tasks(task_contents)
        mock_julius_agent.process_tasks.return_value = [
            results_template._replace(task_content=content) for content in task_contents
        ]
        await orchestrator.run_round() # batch_size will remain 5

    status = orchestrator.get_status()
    assert len(status['last_10_rounds_metrics']) == 10
    assert status['total_metrics_rounds'] == 3 + 10
    # The content of the first metric of the last 10 should be from the "extra_task" series
    first_task_in_preview = status['last_10_rounds_metrics'][0]['results_summary'][0]['task_content']
    assert "extra_task" in first_task_in_preview
    assert "t1" not in first_task_in_preview # Oldest metric should be gone

    orchestrator.mock_log_to_file.assert_called()
    assert orchestrator.mock_log_to_file.call_count == 3 + 10

# To run these tests, navigate to the project root and run:
# python -m pytest
# Ensure __init__.py files are present in tests/ and tests/orchestrator/ if needed for module discovery,
# though with modern pytest and src-layout, it's often not strictly necessary if tests/ is a top-level dir.
# I will add them just in case.

# Adding a test for the _initialize_metrics_log_file behavior with actual file system is more of an integration test.
# Here, we've mocked it out. A separate test could be written that uses `tmp_path` from pytest.
# For now, focusing on the orchestrator's logic.
# Similarly for _log_metric_to_file, we mocked it.
# The test `test_run_round_metrics_collection` checks that `_log_metric_to_file` is called with the correct metric.

async def test_run_round_no_tasks_in_batch_after_pop(orchestrator, mock_julius_agent):
    # This scenario should ideally not happen if batch_size and queue length are handled correctly,
    # but it's a defensive check for the `if not batch_tasks:` line in run_round.

    # Initialize task_queue with a Task object for type consistency
    orchestrator.add_tasks(["task1"]) # Adds Task(content="task1", retries=0, priority=DEFAULT_PRIORITY)
    orchestrator.batch_size = 1

    # Simulate task_queue.pop(0) returning an empty list due to some unexpected state or modification
    # This is hard to simulate directly without complex patching of list.pop itself.
    # The existing logic `actual_batch_size = min(self.batch_size, len(self.task_queue))`
    # and `current_batch_tasks_objects = [self.task_queue.pop(0) for _ in range(actual_batch_size)]`
    # should prevent `current_batch_tasks_objects` from being empty if `actual_batch_size > 0`.
    # If `actual_batch_size` is 0 (queue was empty), it's covered by `test_run_round_empty_queue`.

    # A more direct test: If the queue has tasks, but batch_size is 0
    orchestrator.task_queue.clear()
    orchestrator.add_tasks(["task1"])
    orchestrator.batch_size = 0 # Forcing a situation where actual_batch_size could be 0

    await orchestrator.run_round()

    # In this case, actual_batch_size will be 0.
    # `current_batch_tasks_objects` will be `[]`.
    # The `if not current_batch_tasks_objects:` condition will be true.
    mock_julius_agent.process_tasks.assert_not_called()
    # No new metrics if no tasks processed
    initial_metrics_count = len(orchestrator.metrics_history)
    await orchestrator.run_round()
    assert len(orchestrator.metrics_history) == initial_metrics_count

    # The print statement "No tasks to process in this batch." should have been logged (if logging was enabled for prints).
    # This confirms the `if not current_batch_tasks_objects:` path.
    assert len(orchestrator.task_queue) == 1 # Task queue remains unchanged.
    assert orchestrator.task_queue[0].content == "task1"


# --- New tests for Retry Logic and Priority ---

async def test_task_retry_on_failure(orchestrator, mock_julius_agent):
    task_content = "retry_task"
    orchestrator.add_tasks([task_content])
    orchestrator.batch_size = 1

    # Simulate failure
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Failed for retry test", task_content=task_content)
    ]

    await orchestrator.run_round()

    assert len(orchestrator.task_queue) == 1
    retried_task = orchestrator.task_queue[0]
    assert retried_task.content == task_content
    assert retried_task.retries == 1
    assert retried_task.priority == RETRY_PRIORITY

    metric = orchestrator.metrics_history[0]
    assert metric['failed_tasks_count'] == 1
    assert metric['results_summary'][0]['retries_attempted'] == 0 # First attempt failed


async def test_task_max_retries_give_up(orchestrator, mock_julius_agent):
    task_content = "max_retry_task"
    # Manually set a task with MAX_RETRIES - 1 attempts already done
    task_to_exhaust = Task(content=task_content, retries=MAX_RETRIES -1, priority=RETRY_PRIORITY)
    orchestrator.task_queue.append(task_to_exhaust)
    orchestrator.batch_size = 1

    initial_queue_length = len(orchestrator.task_queue)

    # Simulate failure again
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Failed on last retry attempt", task_content=task_content)
    ]

    await orchestrator.run_round() # This is the MAX_RETRIES attempt

    # Task should not be requeued
    assert len(orchestrator.task_queue) == initial_queue_length -1
    for task_in_q in orchestrator.task_queue: # Ensure it's not the one we were testing
        assert task_in_q.content != task_content

    metric = orchestrator.metrics_history[0]
    assert metric['failed_tasks_count'] == 1
    assert metric['results_summary'][0]['retries_attempted'] == MAX_RETRIES -1
    assert metric['results_summary'][0]['task_content'] == task_content


async def test_priority_processing_retried_tasks_first(orchestrator, mock_julius_agent):
    # Add a normal task first
    orchestrator.add_tasks(["normal_task_low_priority"])
    # Add a task that has been retried (so it has high priority)
    # Manually add to ensure it's "behind" the normal task initially if not sorted
    orchestrator.task_queue.append(
        Task(content="retried_task_high_priority", retries=1, priority=RETRY_PRIORITY)
    )
    # Add another normal task
    orchestrator.add_tasks(["another_normal_task"])

    # Queue before sort (conceptual):
    # normal_task_low_priority (p=10, r=0)
    # retried_task_high_priority (p=1, r=1)
    # another_normal_task (p=10, r=0)
    # After add_tasks, sort is called. And run_round also sorts.

    orchestrator.batch_size = 1 # Process one task at a time

    # Mock agent to always succeed for this test
    mock_julius_agent.process_tasks.side_effect = lambda tasks_batch: \
        [TaskResult(success=True, details="Processed", task_content=tc) for tc in tasks_batch]

    # First run_round should process the high-priority retried task
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_with(["retried_task_high_priority"])
    assert len(orchestrator.task_queue) == 2
    assert orchestrator.task_queue[0].content == "normal_task_low_priority" # Assuming stable sort for same priority
    assert orchestrator.task_queue[1].content == "another_normal_task"

    # Second run_round should process one of the normal tasks
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_with(["normal_task_low_priority"])
    assert len(orchestrator.task_queue) == 1
    assert orchestrator.task_queue[0].content == "another_normal_task"

    # Third run_round should process the last normal task
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_with(["another_normal_task"])
    assert len(orchestrator.task_queue) == 0


async def test_error_types_metric_population(orchestrator, mock_julius_agent):
    tasks_to_fail = ["fail_timeout", "fail_connection", "fail_general", "fail_timeout_again"]
    orchestrator.add_tasks(tasks_to_fail)
    orchestrator.batch_size = len(tasks_to_fail)

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="This task had a timeout error.", task_content="fail_timeout"),
        TaskResult(success=False, details="A connection issue occurred.", task_content="fail_connection"),
        TaskResult(success=False, details="Some other failure.", task_content="fail_general"),
        TaskResult(success=False, details="Another timeout.", task_content="fail_timeout_again"),
    ]

    await orchestrator.run_round()

    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    assert metric['failed_tasks_count'] == 4
    expected_error_types = {
        "TIMEOUT_ERROR": 2,
        "CONNECTION_ERROR": 1,
        "GENERAL_FAILURE": 1
    }
    assert metric['error_types_in_batch'] == expected_error_types

    # Check that tasks were requeued
    assert len(orchestrator.task_queue) == 4
    for task_in_q in orchestrator.task_queue:
        assert task_in_q.retries == 1
        assert task_in_q.priority == RETRY_PRIORITY


async def test_status_with_pending_retries(orchestrator, mock_julius_agent):
    orchestrator.add_tasks(["task_A", "task_B", "task_C"])
    orchestrator.batch_size = 2

    # Fail task A and B, they should be requeued for retry
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="fail A", task_content="task_A"),
        TaskResult(success=False, details="fail B", task_content="task_B"),
    ]
    await orchestrator.run_round() # Processes A, B. Both fail and are requeued. C is still in queue.

    status = orchestrator.get_status()
    assert status['task_queue_length'] == 3 # A (retry), B (retry), C (original)
    assert status['tasks_pending_retry'] == 2 # A and B are pending retry

    # Verify preview shows retry info
    preview_contents = {item['content'] for item in status['task_queue_preview']}
    assert "task_A" in preview_contents
    assert "task_B" in preview_contents
    assert "task_C" in preview_contents

    for item in status['task_queue_preview']:
        if item['content'] == "task_A" or item['content'] == "task_B":
            assert item['retries'] == 1
            assert item['priority'] == RETRY_PRIORITY
        if item['content'] == "task_C":
            assert item['retries'] == 0
            assert item['priority'] == DEFAULT_PRIORITY

    # Process again. Highest priority (retried A and B) should be processed.
    # Assume batch size is still 2.
    # Let's say A succeeds, B fails again.
    mock_julius_agent.process_tasks.side_effect = lambda tasks_batch_content: [
        TaskResult(success=True, details="A success on retry", task_content=tasks_batch_content[0]) # task_A
            if tasks_batch_content[0] == "task_A" else
        TaskResult(success=False, details="B fail again", task_content=tasks_batch_content[1]) # task_B
            if tasks_batch_content[1] == "task_B" else
        TaskResult(success=True, details="Processed", task_content=tasks_batch_content[0]) # Fallback for C
    ]

    await orchestrator.run_round() # Processes retried A and B. A succeeds, B fails (retry 2).
                                   # Queue: B (retry 2, p=1), C (original, p=10)

    status = orchestrator.get_status()
    assert status['task_queue_length'] == 2
    assert status['tasks_pending_retry'] == 1 # Only B is pending its 2nd retry

    found_b_in_preview = False
    for item in status['task_queue_preview']:
        if item['content'] == "task_B":
            assert item['retries'] == 2
            assert item['priority'] == RETRY_PRIORITY
            found_b_in_preview = True
    assert found_b_in_preview
