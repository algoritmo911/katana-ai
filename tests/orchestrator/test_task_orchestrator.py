import asyncio
import pytest
from unittest.mock import AsyncMock, patch, call # Using AsyncMock for async methods

# Adjust import path based on how pytest will discover your modules.
# If tests/ is at the same level as src/, and you run pytest from project root:
from src.orchestrator.task_orchestrator import TaskOrchestrator, TaskResult
from src.agents.julius_agent import JuliusAgent # Needed for type hinting mock

# Pytest needs to be able to run async tests
pytestmark = pytest.mark.asyncio

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
    tasks = ["task1", "task2"]
    orchestrator.add_tasks(tasks)
    assert orchestrator.task_queue == tasks
    orchestrator.add_tasks(["task3"])
    assert orchestrator.task_queue == ["task1", "task2", "task3"]


async def test_run_round_empty_queue(orchestrator, mock_julius_agent):
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_not_called()
    assert len(orchestrator.metrics_history) == 0
    orchestrator.mock_log_to_file.assert_not_called()


async def test_run_round_all_success_increase_batch_size(orchestrator, mock_julius_agent):
    tasks = ["task1", "task2", "task3"]
    orchestrator.add_tasks(tasks)
    orchestrator.batch_size = 2 # Initial batch size for this test

    # Mock agent to return all success
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2"])
    assert orchestrator.batch_size == 3 # Increased from 2
    assert len(orchestrator.task_queue) == 1 # task3 remaining
    assert len(orchestrator.metrics_history) == 1
    assert orchestrator.metrics_history[0]['successful_tasks_count'] == 2
    assert orchestrator.metrics_history[0]['failed_tasks_count'] == 0
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_all_success_at_max_batch_size(orchestrator, mock_julius_agent):
    orchestrator.batch_size = orchestrator.max_batch # Start at max batch
    orchestrator.add_tasks(["task1", "task2"])

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]
    await orchestrator.run_round()
    assert orchestrator.batch_size == orchestrator.max_batch # Stays at max
    orchestrator.mock_log_to_file.assert_called_once()

async def test_run_round_multiple_failures_decrease_batch_size(orchestrator, mock_julius_agent):
    tasks = ["task1", "task2", "task3"] # orchestrator default batch_size is 2
    orchestrator.add_tasks(tasks)
    orchestrator.batch_size = 3 # Set higher for test

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail", task_content="task1"),
        TaskResult(success=False, details="Fail", task_content="task2"),
        TaskResult(success=True, details="Success", task_content="task3"),
    ]

    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2", "task3"])
    assert orchestrator.batch_size == 2 # Decreased from 3
    assert len(orchestrator.task_queue) == 0
    assert len(orchestrator.metrics_history) == 1
    assert orchestrator.metrics_history[0]['successful_tasks_count'] == 1
    assert orchestrator.metrics_history[0]['failed_tasks_count'] == 2
    orchestrator.mock_log_to_file.assert_called_once()

async def test_run_round_multiple_failures_at_min_batch_size(orchestrator, mock_julius_agent):
    orchestrator.batch_size = orchestrator.min_batch_size # Start at min (1)
    orchestrator.add_tasks(["task1", "task2"]) # Add two tasks

    # First round processes 1 task (min_batch_size), it fails
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail", task_content="task1")
    ]
    await orchestrator.run_round() # Processes task1
    # Batch size should remain min_batch_size even with a failure, as it only decreases with >1 failure in a batch
    # And a batch of 1 cannot have >1 failure.
    assert orchestrator.batch_size == orchestrator.min_batch_size
    assert mock_julius_agent.process_tasks.call_count == 1
    mock_julius_agent.process_tasks.assert_called_with(["task1"])

    # If we had a batch size of 2, and both failed:
    orchestrator.batch_size = 2
    orchestrator.task_queue.clear()
    orchestrator.add_tasks(["task_A", "task_B"])
    mock_julius_agent.process_tasks.reset_mock() # Reset mock for the new call
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail", task_content="task_A"),
        TaskResult(success=False, details="Fail", task_content="task_B"),
    ]
    await orchestrator.run_round()
    assert orchestrator.batch_size == 1 # Decreased to min_batch_size
    orchestrator.mock_log_to_file.assert_called()


async def test_run_round_single_failure_no_batch_size_change(orchestrator, mock_julius_agent):
    orchestrator.batch_size = 3
    orchestrator.add_tasks(["task1", "task2", "task3"])
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=False, details="Fail", task_content="task2"),
        TaskResult(success=True, details="Success", task_content="task3"),
    ]
    await orchestrator.run_round()
    assert orchestrator.batch_size == 3 # No change for single failure
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_processes_fewer_than_batch_size_if_queue_small(orchestrator, mock_julius_agent):
    orchestrator.batch_size = 5
    orchestrator.add_tasks(["task1", "task2"]) # Only 2 tasks in queue
    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(["task1", "task2"])
    assert len(orchestrator.task_queue) == 0
    # Batch size should increase because all processed tasks were successful
    assert orchestrator.batch_size == 5 # Stays 5, then increases to max_batch (5 in this test) + 1, capped at max_batch
                                        # Oh, wait, max_batch is 5. So it should be 5.
                                        # Original batch_size=2, max_batch=5
                                        # If orchestrator.batch_size = 5, it should not increase.
                                        # Let's re-evaluate the fixture: batch_size=2, max_batch=5
                                        # So if current batch_size = 2, and we process 2 tasks successfully, it should go to 3.

    # Resetting for clarity with fixture values (initial batch_size=2)
    orchestrator.batch_size = 2 # from fixture
    orchestrator.task_queue.clear()
    orchestrator.metrics_history.clear()
    mock_julius_agent.process_tasks.reset_mock()
    orchestrator.mock_log_to_file.reset_mock()

    orchestrator.add_tasks(["taskA"]) # Queue smaller than batch_size
    mock_julius_agent.process_tasks.return_value = [TaskResult(success=True, details="S", task_content="taskA")]

    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(["taskA"])
    assert orchestrator.batch_size == 3 # Increased because the single task was successful
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_metrics_collection(orchestrator, mock_julius_agent):
    orchestrator.add_tasks(["task1"])
    mock_julius_agent.process_tasks.return_value = [TaskResult(success=True, details="S", task_content="task1")]

    await orchestrator.run_round()
    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    assert metric['batch_size_at_round_start'] == orchestrator.batch_size -1 # because it was incremented
    assert metric['tasks_processed_count'] == 1
    assert metric['successful_tasks_count'] == 1
    assert metric['failed_tasks_count'] == 0
    assert metric['success_rate'] == 1.0
    assert 'time_taken_seconds' in metric
    assert metric['batch_tasks_content'] == ["task1"]
    assert len(metric['results_summary']) == 1
    assert metric['results_summary'][0]['task'] == "task1"
    assert metric['results_summary'][0]['success'] is True
    orchestrator.mock_log_to_file.assert_called_once_with(metric)


async def test_get_status_method(orchestrator, mock_julius_agent):
    orchestrator.add_tasks(["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10", "t11"]) # 11 tasks
    orchestrator.batch_size = 3 # from fixture it's 2, let's set it for test

    # Simulate a few rounds to populate metrics_history
    results_template = [TaskResult(success=True, details="S", task_content="")]

    mock_julius_agent.process_tasks.return_value = [results_template[0]._replace(task_content=f"t{i}") for i in range(1,4)] # tasks t1,t2,t3
    await orchestrator.run_round() # Processes 3, batch_size becomes 4

    mock_julius_agent.process_tasks.return_value = [results_template[0]._replace(task_content=f"t{i}") for i in range(4,8)] # tasks t4,t5,t6,t7
    await orchestrator.run_round() # Processes 4, batch_size becomes 5 (max)

    mock_julius_agent.process_tasks.return_value = [results_template[0]._replace(task_content=f"t{i}") for i in range(8,12)] # tasks t8,t9,t10,t11
    await orchestrator.run_round() # Processes 4 (queue has 4 left), batch_size stays 5

    status = orchestrator.get_status()
    assert status['current_batch_size'] == 5 # Max batch size
    assert status['task_queue_length'] == 0 # 3+4+4 = 11 tasks processed
    assert status['total_metrics_rounds'] == 3
    assert len(status['last_10_rounds_metrics']) == 3 # All 3 rounds are part of last 10

    # Simulate more rounds to test "last_10_rounds_metrics"
    for i in range(10): # 7 more rounds + 3 existing = 10. Then 1 more.
        orchestrator.add_tasks([f"extra_task_{j}" for j in range(orchestrator.batch_size)])
        mock_julius_agent.process_tasks.return_value = [
            results_template[0]._replace(task_content=f"extra_task_{j}") for j in range(orchestrator.batch_size)
        ]
        await orchestrator.run_round() # batch_size will remain 5

    status = orchestrator.get_status()
    assert len(status['last_10_rounds_metrics']) == 10
    assert status['total_metrics_rounds'] == 3 + 10
    assert status['last_10_rounds_metrics'][0]['batch_tasks_content'][0] != "t1" # Oldest metric should be gone

    orchestrator.mock_log_to_file.assert_called() # Ensure logging happened
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
    orchestrator.task_queue = ["task1"]
    orchestrator.batch_size = 1

    # Simulate task_queue.pop(0) returning an empty list due to some unexpected state or modification
    # This is hard to simulate directly without complex patching of list.pop itself.
    # The existing logic `actual_batch_size = min(self.batch_size, len(self.task_queue))`
    # and `batch_tasks = [self.task_queue.pop(0) for _ in range(actual_batch_size)]`
    # should prevent `batch_tasks` from being empty if `actual_batch_size > 0`.
    # If `actual_batch_size` is 0 (queue was empty), it's covered by `test_run_round_empty_queue`.

    # Let's assume the queue becomes empty *after* `actual_batch_size` is determined but before popping.
    # This is also unlikely with current synchronous logic within run_round.
    # The `if not batch_tasks:` check is more of a safeguard.

    # A more direct test: If the queue has tasks, but batch_size is 0 (or < min_batch_size, though constructor prevents 0).
    # The current logic for `actual_batch_size` would be `min(0, len(queue))`, so 0.
    # `batch_tasks` would be `[]`.
    orchestrator.task_queue = ["task1"]
    orchestrator.batch_size = 0 # Forcing a situation where actual_batch_size could be 0

    await orchestrator.run_round()

    # In this case, actual_batch_size will be 0.
    # The `batch_tasks = [self.task_queue.pop(0) for _ in range(actual_batch_size)]` will result in an empty list.
    # The `if not batch_tasks:` condition will be true.
    mock_julius_agent.process_tasks.assert_not_called()
    assert len(orchestrator.metrics_history) == 0
    orchestrator.mock_log_to_file.assert_not_called()
    # The print statement "No tasks to process in this batch." should have been logged (if logging was enabled for prints).
    # This confirms the `if not batch_tasks:` path.
    assert orchestrator.task_queue == ["task1"] # Task queue remains unchanged.

    # Test with batch_size 1, queue becomes empty unexpectedly after check (hard to test cleanly)
    # The current code is robust against this unless `self.task_queue.pop(0)` itself raises an error
    # not caught, which would fail the test anyway.
