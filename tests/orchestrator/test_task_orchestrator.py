import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from src.orchestrator.task_orchestrator import TaskOrchestrator, TaskResult
from src.agents.julius_agent import JuliusAgent
import redis

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_julius_agent(mocker):
    """Fixture to create a mock JuliusAgent."""
    agent = mocker.MagicMock(spec=JuliusAgent)
    agent.process_tasks = AsyncMock()
    return agent

@pytest.fixture
def mock_redis_client(mocker):
    """Fixture to create a mock Redis client."""
    mock_client = mocker.MagicMock(spec=redis.Redis)
    mock_client.ping.return_value = True
    mock_client.llen.return_value = 0
    mock_pipeline = mocker.MagicMock()
    mock_pipeline.execute.return_value = [[]]
    mock_client.pipeline.return_value = mock_pipeline
    return mock_client

@pytest.fixture
def orchestrator(mock_julius_agent, mock_redis_client, mocker):
    """Fixture to create a TaskOrchestrator instance with mocked dependencies."""
    with patch('redis.Redis', return_value=mock_redis_client):
        with patch.object(TaskOrchestrator, '_initialize_metrics_log_file', return_value=None), \
             patch.object(TaskOrchestrator, '_log_metric_to_file', return_value=None) as mock_log_to_file:
            instance = TaskOrchestrator(
                agent=mock_julius_agent,
                redis_host='mock_host',
                redis_port=6379,
                redis_db=0,
                batch_size=2,
                max_batch=5
            )
            instance.mock_log_to_file = mock_log_to_file
            instance.mock_redis_client = mock_redis_client
            yield instance

def setup_redis_queue(mock_redis_client, all_tasks, batch_tasks):
    """Helper to configure the mock redis client for a test."""
    mock_redis_client.llen.return_value = len(all_tasks)
    pipeline_mock = mock_redis_client.pipeline.return_value
    # The pipeline's execute returns a list of results for each command.
    # Here, the first command is lrange, so its result is the list of tasks.
    pipeline_mock.execute.return_value = [[t.encode('utf-8') for t in batch_tasks]]

# --- Test Cases ---

async def test_orchestrator_initialization(orchestrator, mock_julius_agent):
    assert orchestrator.agent == mock_julius_agent
    orchestrator.mock_redis_client.ping.assert_called_once()

async def test_run_round_empty_queue(orchestrator, mock_julius_agent):
    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_not_called()

async def test_run_round_all_success_increase_batch_size(orchestrator, mock_julius_agent):
    all_tasks = ["task1", "task2", "task3"]
    batch_tasks = ["task1", "task2"] # Expecting a batch of 2
    setup_redis_queue(orchestrator.mock_redis_client, all_tasks, batch_tasks)
    orchestrator.batch_size = 2

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=True, details="Success", task_content="task1"),
        TaskResult(success=True, details="Success", task_content="task2"),
    ]

    await orchestrator.run_round()

    mock_julius_agent.process_tasks.assert_called_once_with(batch_tasks)
    assert orchestrator.batch_size == 3
    orchestrator.mock_redis_client.pipeline.return_value.ltrim.assert_called_once_with(orchestrator.task_queue_name, 2, -1)

async def test_run_round_multiple_failures_decrease_batch_size(orchestrator, mock_julius_agent):
    all_tasks = ["task1", "task2", "task3"]
    setup_redis_queue(orchestrator.mock_redis_client, all_tasks, all_tasks)
    orchestrator.batch_size = 3

    mock_julius_agent.process_tasks.return_value = [
        TaskResult(success=False, details="Fail", task_content="task1"),
        TaskResult(success=False, details="Fail", task_content="task2"),
        TaskResult(success=True, details="Success", task_content="task3"),
    ]

    await orchestrator.run_round()
    mock_julius_agent.process_tasks.assert_called_once_with(all_tasks)
    assert orchestrator.batch_size == 2

async def test_run_round_metrics_collection(orchestrator, mock_julius_agent):
    tasks = ["task1"]
    setup_redis_queue(orchestrator.mock_redis_client, tasks, tasks)
    mock_julius_agent.process_tasks.return_value = [TaskResult(success=True, details="S", task_content="task1")]

    await orchestrator.run_round()
    assert len(orchestrator.metrics_history) == 1
    metric = orchestrator.metrics_history[0]
    assert metric['tasks_processed_count'] == 1
    orchestrator.mock_log_to_file.assert_called_once_with(metric)

async def test_get_status_method(orchestrator):
    orchestrator.mock_redis_client.llen.return_value = 11
    orchestrator.batch_size = 3

    status = orchestrator.get_status()
    assert status['task_queue_length'] == 11
    orchestrator.mock_redis_client.llen.assert_called_once_with(orchestrator.task_queue_name)
