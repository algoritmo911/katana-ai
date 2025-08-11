import pytest
import json
import os
import asyncio
import main
from unittest.mock import MagicMock

# The components to be tested
from main import run_autonomous_loop
from src.orchestrator.task_orchestrator import TaskOrchestrator, KatanaTaskProcessor
from src.memory.memory_manager import MemoryManager

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

# A custom exception to break the loop after one iteration
class StopTestLoop(Exception):
    pass

@pytest.fixture
def orchestrator_log_file(tmp_path):
    """Creates a dummy orchestrator log file for testing."""
    log_file = tmp_path / "orchestrator_log.json"

    # This log data is designed to trigger the self-healer
    high_failure_log = [
        {
            "timestamp": "2025-08-11T15:00:00Z",
            "tasks_processed_count": 4,
            "failed_tasks_count": 3,
            "success_rate": 0.25,
            "results_summary": [
                {"task": {"type": "n8n_workflow_generation"}, "success": False},
                {"task": {"type": "text_generation"}, "success": False},
                {"task": {"type": "n8n_workflow_generation"}, "success": True},
                {"task": {"type": "text_generation"}, "success": False},
            ]
        }
    ]
    with open(log_file, 'w') as f:
        json.dump(high_failure_log, f)

    # Override the global constant in the main module for the duration of the test
    original_log_file = main.ORCHESTRATOR_LOG_FILE
    main.ORCHESTRATOR_LOG_FILE = str(log_file)
    yield str(log_file)
    main.ORCHESTRATOR_LOG_FILE = original_log_file # Restore
    os.remove(log_file)


@pytest.fixture
def mock_memory_manager(mocker):
    """Mocks the MemoryManager to avoid Redis dependency."""
    mock = mocker.MagicMock(spec=MemoryManager)
    mock.redis_client = True # Simulate a successful connection
    mock.get_history.return_value = [] # Default to no history
    return mock


async def test_full_autonomous_loop_generates_healing_task(mocker, orchestrator_log_file, mock_memory_manager):
    """
    Integration test for the full autonomous loop.
    Verifies that the system can detect its own failures from logs and
    generate a corrective task.
    """
    # 1. Setup: Patch asyncio.sleep to break the loop after one iteration
    mocker.patch('asyncio.sleep', side_effect=StopTestLoop)

    # 2. Setup: Instantiate the core components for the test
    task_processor = KatanaTaskProcessor()
    orchestrator = TaskOrchestrator(
        agent=task_processor,
        metrics_log_file=orchestrator_log_file # Use the test log file
    )

    # 3. Execution: Run the autonomous loop for one iteration.
    # We mock the run_round method itself so we can inspect the queue
    # before the tasks are processed.
    mocker.patch.object(orchestrator, 'run_round', return_value=None)

    try:
        await run_autonomous_loop(orchestrator, mock_memory_manager)
    except StopTestLoop:
        print("Autonomous loop successfully intercepted after one iteration.")

    # 4. Assertions: Check the state of the orchestrator's queue.
    assert len(orchestrator.task_queue) > 0, "Task queue should not be empty after the loop."

    # The loop should have generated one healing task and one DAO task.
    assert len(orchestrator.task_queue) == 2, f"Expected 2 tasks in the queue, but found {len(orchestrator.task_queue)}"

    # Check for the self-healing task
    healing_task_found = any(task['type'] == 'self_healing_diagnostics' for task in orchestrator.task_queue)
    assert healing_task_found, "A self-healing diagnostics task was not found in the queue."

    # Check for the DAO-generated task
    dao_task_found = any(task['type'] == 'n8n_workflow_generation' for task in orchestrator.task_queue)
    assert dao_task_found, "A DAO-generated n8n workflow task was not found in the queue."

    print("Test passed: The autonomous loop correctly generated both a self-healing task and a DAO task.")
