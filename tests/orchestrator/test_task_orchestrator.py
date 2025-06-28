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
    agent = mocker.MagicMock(spec=JuliusAgent)
    agent.process_tasks = AsyncMock()
    return agent

@pytest.fixture
def mock_self_evolver(mocker):
    """Fixture to create a mock SelfEvolver."""
    evolver = mocker.MagicMock() # Not using spec here as it might not be available if import fails
    evolver.generate_patch = mocker.MagicMock(return_value=None) # Default: no patch
    evolver.apply_patch = mocker.MagicMock(return_value=False)  # Default: apply fails
    return evolver

@pytest.fixture
def orchestrator(mock_julius_agent, mock_self_evolver, mocker):
    """Fixture to create a TaskOrchestrator instance with mocked agent and evolver."""
    # Patch the SelfEvolver class where TaskOrchestrator looks for it
    # This ensures that TaskOrchestrator uses our mock_self_evolver instance.
    # We also need to handle the case where SelfEvolver might be None if the import failed.
    # So, we patch 'src.orchestrator.task_orchestrator.SelfEvolver'

    # To correctly mock SelfEvolver, especially its conditional import and instantiation:
    # 1. If SelfEvolver is imported and used as a class: patch('...SelfEvolver')
    # 2. If an instance is created and assigned: patch.object(module, 'instance_name')

    # In TaskOrchestrator, `self.self_evolver = SelfEvolver()` happens if SelfEvolver is not None.
    # So, we patch the class `SelfEvolver` that is imported at the module level.

    # Temporarily allow SelfEvolver to be mocked even if it's None in the actual import
    # This is a bit tricky due to the conditional import.
    # The easiest way is to ensure `task_orchestrator.SelfEvolver` points to our mock class,
    # which then returns our mock_self_evolver instance when called.

    mock_self_evolver_class = mocker.MagicMock(return_value=mock_self_evolver)

    with patch('src.orchestrator.task_orchestrator.SelfEvolver', mock_self_evolver_class) as mock_evolver_cls_ref, \
         patch.object(TaskOrchestrator, '_initialize_metrics_log_file', return_value=None), \
         patch.object(TaskOrchestrator, '_log_metric_to_file', return_value=None) as mock_log_to_file:

        # If SelfEvolver was None due to import error, the mock_evolver_cls_ref won't be used by TaskOrchestrator.
        # We need to ensure TaskOrchestrator *thinks* SelfEvolver was imported.
        # A simple way for testing is to force task_orchestrator.SelfEvolver to our mock class *before* TaskOrchestrator is init'd.
        # The patch above should handle this. If SelfEvolver was originally None, TaskOrchestrator would have self.self_evolver = None.
        # By patching it to a mock class, TaskOrchestrator will try to instantiate it.

        instance = TaskOrchestrator(agent=mock_julius_agent, batch_size=2, max_batch=5)

        # If the mock_evolver_cls_ref was used, instance.self_evolver should be our mock_self_evolver.
        # If SelfEvolver was None in the module after import, instance.self_evolver would be None.
        # The test setup needs to ensure that for auto-patching tests, self.self_evolver is the mock.
        # The patch effectively makes src.orchestrator.task_orchestrator.SelfEvolver the mock_self_evolver_class.
        # So, when TaskOrchestrator initializes, it calls mock_self_evolver_class() which returns mock_self_evolver.

        # We can assert this:
        if mock_evolver_cls_ref is not None : # If SelfEvolver was patchable (i.e., not None from failed import)
             assert instance.self_evolver == mock_self_evolver, "SelfEvolver mock not correctly injected"

        instance.mock_log_to_file = mock_log_to_file
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
    pass


# --- Auto-Patching Test Cases ---

async def test_run_round_autopatch_success(orchestrator, mock_julius_agent, mock_self_evolver):
    """Test successful auto-patching: fail -> patch generated -> patch applied -> re-verify success."""
    task_content = "failed_task_to_patch"
    orchestrator.add_tasks([task_content])
    # Ensure the orchestrator instance uses the mock_self_evolver from the fixture
    # This should be handled by the fixture's patching of 'src.orchestrator.task_orchestrator.SelfEvolver'
    assert orchestrator.self_evolver is mock_self_evolver


    # Initial processing: task fails
    mock_julius_agent.process_tasks.side_effect = [
        [TaskResult(success=False, details="Initial error", task_content=task_content)], # Initial call
        [TaskResult(success=True, details="Fixed by patch", task_content=task_content)]  # Re-verification call
    ]

    mock_self_evolver.generate_patch.return_value = "dummy_patch_content"
    mock_self_evolver.apply_patch.return_value = True

    await orchestrator.run_round()

    assert mock_julius_agent.process_tasks.call_count == 2
    mock_julius_agent.process_tasks.assert_any_call([task_content]) # Both calls process this single task

    mock_self_evolver.generate_patch.assert_called_once_with("Initial error")
    mock_self_evolver.apply_patch.assert_called_once_with("dummy_patch_content")

    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 1 # Final success
    assert metric['failed_tasks_count'] == 0

    summary = metric['results_summary'][0]
    assert summary['task'] == task_content
    assert summary['success'] is True # Final success
    assert summary['details'] == "Initial error" # Original error
    assert summary['patched_attempted'] is True
    assert summary['patch_suggested_content'] == "dummy_patch_content"
    assert summary['patch_applied_successfully'] is True
    assert summary['success_after_patch'] is True
    assert summary['details_after_patch'] == "Fixed by patch"
    orchestrator.mock_log_to_file.assert_called_once()


async def test_run_round_autopatch_generation_fails(orchestrator, mock_julius_agent, mock_self_evolver):
    """Test auto-patching: fail -> no patch generated -> task remains failed."""
    task_content = "failed_task_no_patch"
    orchestrator.add_tasks([task_content])
    assert orchestrator.self_evolver is mock_self_evolver

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Error, no patch expected", task_content=task_content)
    ]
    mock_self_evolver.generate_patch.return_value = None # No patch generated

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with([task_content])
    mock_self_evolver.generate_patch.assert_called_once_with("Error, no patch expected")
    mock_self_evolver.apply_patch.assert_not_called()

    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 0
    assert metric['failed_tasks_count'] == 1

    summary = metric['results_summary'][0]
    assert summary['success'] is False
    assert summary['patched_attempted'] is True
    assert summary['patch_suggested_content'] is None
    assert summary['patch_applied_successfully'] is None
    assert summary['success_after_patch'] is None


async def test_run_round_autopatch_application_fails(orchestrator, mock_julius_agent, mock_self_evolver):
    """Test auto-patching: fail -> patch generated -> patch apply fails -> task remains failed."""
    task_content = "failed_task_apply_fails"
    orchestrator.add_tasks([task_content])
    assert orchestrator.self_evolver is mock_self_evolver

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Error, patch apply will fail", task_content=task_content)
    ]
    mock_self_evolver.generate_patch.return_value = "dummy_patch_content"
    mock_self_evolver.apply_patch.return_value = False # Patch application fails

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with([task_content]) # Only initial call
    mock_self_evolver.generate_patch.assert_called_once_with("Error, patch apply will fail")
    mock_self_evolver.apply_patch.assert_called_once_with("dummy_patch_content")

    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 0
    assert metric['failed_tasks_count'] == 1

    summary = metric['results_summary'][0]
    assert summary['success'] is False
    assert summary['patched_attempted'] is True
    assert summary['patch_suggested_content'] == "dummy_patch_content"
    assert summary['patch_applied_successfully'] is False
    assert summary['success_after_patch'] is None


async def test_run_round_autopatch_reverify_fails(orchestrator, mock_julius_agent, mock_self_evolver):
    """Test auto-patching: fail -> patch generated -> patch applied -> re-verify fails."""
    task_content = "failed_task_reverify_fails"
    orchestrator.add_tasks([task_content])
    assert orchestrator.self_evolver is mock_self_evolver

    mock_julius_agent.process_tasks.side_effect = [
        [TaskResult(success=False, details="Initial error", task_content=task_content)],
        [TaskResult(success=False, details="Still fails after patch", task_content=task_content)] # Re-verification fails
    ]
    mock_self_evolver.generate_patch.return_value = "dummy_patch_content"
    mock_self_evolver.apply_patch.return_value = True

    await orchestrator.run_round()

    assert mock_julius_agent.process_tasks.call_count == 2
    mock_self_evolver.generate_patch.assert_called_once_with("Initial error")
    mock_self_evolver.apply_patch.assert_called_once_with("dummy_patch_content")

    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 0
    assert metric['failed_tasks_count'] == 1

    summary = metric['results_summary'][0]
    assert summary['success'] is False # Final status
    assert summary['details'] == "Initial error"
    assert summary['patched_attempted'] is True
    assert summary['patch_suggested_content'] == "dummy_patch_content"
    assert summary['patch_applied_successfully'] is True
    assert summary['success_after_patch'] is False
    assert summary['details_after_patch'] == "Still fails after patch"


async def test_run_round_no_self_evolver(orchestrator, mock_julius_agent, mock_self_evolver):
    """Test behavior when self_evolver is None (e.g., import failed)."""
    task_content = "failed_task_no_evolver"
    orchestrator.add_tasks([task_content])

    # To simulate SelfEvolver not being available, we set orchestrator.self_evolver to None directly.
    # This overrides what the fixture might have set up if SelfEvolver class was successfully patched.
    orchestrator.self_evolver = None

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Error, no evolver", task_content=task_content)
    ]

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with([task_content])
    # mock_self_evolver is the mock object that would have been used if orchestrator.self_evolver was not None.
    # Since orchestrator.self_evolver is None, its methods should not be called.
    mock_self_evolver.generate_patch.assert_not_called()
    mock_self_evolver.apply_patch.assert_not_called()

    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 0
    assert metric['failed_tasks_count'] == 1

    summary = metric['results_summary'][0]
    assert summary['success'] is False
    # Default values from TaskResult for patch fields should be used
    # The TaskResult is created with defaults if not patched.
    assert summary['patched_attempted'] is False # Because self_evolver was None
    assert summary['patch_suggested_content'] is None
    assert summary['patch_applied_successfully'] is None
    assert summary['success_after_patch'] is None


async def test_run_round_initial_success_no_patch_attempt(orchestrator, mock_julius_agent, mock_self_evolver):
    """Test that patching is not attempted if task is initially successful."""
    task_content = "successful_task"
    orchestrator.add_tasks([task_content])
    assert orchestrator.self_evolver is mock_self_evolver


    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Initial success", task_content=task_content)
    ]

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with([task_content])
    # Check against the instance of evolver used by orchestrator
    orchestrator.self_evolver.generate_patch.assert_not_called()
    orchestrator.self_evolver.apply_patch.assert_not_called()

    metric = orchestrator.metrics_history[0]
    assert metric['successful_tasks_count'] == 1
    assert metric['failed_tasks_count'] == 0

    summary = metric['results_summary'][0]
    assert summary['success'] is True
    assert summary['details'] == "Initial success"
    # These fields should reflect that no patching was done or attempted
    # The TaskResult is created with defaults.
    assert summary['patched_attempted'] is False
    assert summary['patch_suggested_content'] is None
    assert summary['patch_applied_successfully'] is None
    assert summary['success_after_patch'] is None
    assert summary['details_after_patch'] is None

# Ensure the orchestrator fixture correctly injects the mock_self_evolver
# The `orchestrator` fixture has been updated to patch `src.orchestrator.task_orchestrator.SelfEvolver`
# so that the TaskOrchestrator instance uses the provided `mock_self_evolver`.
# The assertion `assert instance.self_evolver == mock_self_evolver` in the fixture helps confirm this.
# If `src.orchestrator.task_orchestrator.SelfEvolver` is `None` (due to import failure in actual code),
# then `instance.self_evolver` will be `None`. The test `test_run_round_no_self_evolver` covers this.
# For other autopatching tests, we assume `instance.self_evolver` is the `mock_self_evolver`.
# The fixture's patch ensures this by making `src.orchestrator.task_orchestrator.SelfEvolver` (the class)
# return `mock_self_evolver` (the instance) when called.
