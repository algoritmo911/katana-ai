import asyncio
import pytest
import pytest_asyncio
import fakeredis.aioredis

from katana.task_queue.models import Task
from katana.task_queue.redis_broker import RedisBroker
from katana.task_queue.service import TaskQueueService
from katana.orchestrator_agent import OrchestratorAgent

# --- Test Setup ---


@pytest_asyncio.fixture(scope="function")
async def redis_broker() -> RedisBroker:
    """Provides a RedisBroker instance using a mocked in-memory Redis."""
    broker = RedisBroker(redis_url="redis://localhost:6379/0")
    fake_redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    broker.redis = fake_redis_client
    yield broker
    await fake_redis_client.flushall()
    await broker.close()


# --- Mock Worker Executors ---


async def mock_web_search_executor(query: str):
    return f"Mock web results for '{query}'"


async def mock_financial_data_executor(company: str, report: str):
    return f"Mock financial report for {company}"


async def mock_predictive_analysis_executor(data_sources: list, target: str):
    return f"Mock prediction for {target}"


@pytest.mark.asyncio
async def test_e2e_orchestrator_and_workers(redis_broker: RedisBroker):
    """
    Tests the full end-to-end cycle of the collective intelligence system.
    """
    # 1. Setup the environment
    task_executors = {
        "web_search": mock_web_search_executor,
        "financial_data_api": mock_financial_data_executor,
        "predictive_analysis": mock_predictive_analysis_executor,
    }

    task_queue_service = TaskQueueService(
        broker=redis_broker, task_executors=task_executors
    )
    orchestrator = OrchestratorAgent(
        task_queue_service=task_queue_service, broker=redis_broker
    )

    # 2. Start the worker service in the background
    worker_tasks = task_queue_service.start_workers(num_workers=3, poll_interval=0.1)

    # 3. Define the complex query that triggers all mock executors
    complex_query = "Проанализируй новости о Nvidia, собери финансовые отчеты и сделай прогноз по акциям."

    # 4. Handle the query with the orchestrator
    final_report = await orchestrator.handle_complex_query(complex_query)

    # 5. Assert the final report is correct
    assert "Итоговый отчет" in final_report
    assert "Mock web results for 'Nvidia news last 24 hours'" in final_report
    assert "Mock financial report for NVDA" in final_report
    assert "Mock prediction for NVDA stock price next week" in final_report

    # 6. Graceful shutdown
    await task_queue_service.shutdown()

    await asyncio.sleep(0.2)

    for task in worker_tasks:
        assert task.done() is True