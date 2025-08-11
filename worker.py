import asyncio
import logging

from katana.task_queue.redis_broker import RedisBroker
from katana.task_queue.service import TaskQueueService
from katana.task_queue.models import Task
from logging_config import setup_logging

# Configure logging for the worker
setup_logging(logging.INFO)
logger = logging.getLogger("KatanaWorker")

# --- Worker Configuration ---
REDIS_URL = "redis://localhost:6379/0"
NUM_WORKERS = 4  # Number of concurrent tasks this worker process can handle

# --- Task Executor Functions ---
# These are the implementations of the "specialized agents".
# In a real, large-scale application, these might be in their own modules.


async def web_search_executor(task: Task):
    """
    Executor for 'web_search' tasks.
    Simulates searching the web for a query.
    """
    query = task.payload.get("query", "no query specified")
    logger.info(f"[WebSearcher] Received task {task.id}. Searching for: '{query}'")

    # Simulate I/O-bound work (e.g., making an HTTP request)
    await asyncio.sleep(2)

    result_data = (
        f"Web search results for '{query}': Nvidia stock is up, new AI chip announced."
    )
    logger.info(f"[WebSearcher] Task {task.id} completed. Result: '{result_data}'")
    return result_data


async def financial_data_api_executor(task: Task):
    """
    Executor for 'financial_data_api' tasks.
    Simulates fetching financial data from an API.
    """
    company = task.payload.get("company", "UNKNOWN")
    report = task.payload.get("report", "UNKNOWN")
    logger.info(
        f"[FinancialAgent] Received task {task.id}. Fetching report '{report}' for company '{company}'"
    )

    await asyncio.sleep(3)  # Simulate API call

    result_data = f"Financial data for {company}, report {report}: Revenue is $50B, Profit is $20B."
    logger.info(f"[FinancialAgent] Task {task.id} completed. Result: '{result_data}'")
    return result_data


async def predictive_analysis_executor(task: Task):
    """
    Executor for 'predictive_analysis' tasks.
    Simulates running a predictive model.
    """
    data_sources = task.payload.get("data_sources", [])
    target = task.payload.get("target", "unknown target")
    logger.info(
        f"[AnalysisAgent] Received task {task.id}. Running prediction for '{target}' using sources: {data_sources}"
    )

    await asyncio.sleep(5)  # Simulate heavy computation

    result_data = f"Predictive analysis for {target}: Forecast is a 15% price increase over the next 7 days."
    logger.info(f"[AnalysisAgent] Task {task.id} completed. Result: '{result_data}'")
    return result_data


# --- Main Worker Entry Point ---


async def main():
    """
    Initializes and runs the task queue worker service.
    """
    logger.info("--- Katana Worker Process Starting ---")

    # 1. Define the mapping of task names to their executor functions
    task_executors = {
        "web_search": web_search_executor,
        "financial_data_api": financial_data_api_executor,
        "predictive_analysis": predictive_analysis_executor,
    }
    logger.info(f"Registered task executors: {list(task_executors.keys())}")

    # 2. Initialize the RedisBroker
    broker = RedisBroker(redis_url=REDIS_URL)
    logger.info(f"Connecting to Redis at {REDIS_URL}")

    # 3. Initialize the TaskQueueService
    service = TaskQueueService(broker=broker, task_executors=task_executors)

    # 4. Start the worker tasks
    logger.info(f"Starting {NUM_WORKERS} concurrent worker tasks...")
    worker_tasks = service.start_workers(num_workers=NUM_WORKERS, poll_interval=1.0)

    # 5. Keep the worker alive and handle graceful shutdown
    try:
        # Wait for all worker tasks to complete. They run indefinitely until shutdown is called.
        await asyncio.gather(*worker_tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Initiating graceful shutdown of worker process...")
        await service.shutdown()
        await broker.close()
        logger.info("--- Katana Worker Process Stopped ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker process terminated by user.")
