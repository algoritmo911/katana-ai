# Katana Asynchronous Task Queue Module

This module implements an asynchronous task queue system with support for priorities, delayed execution, and basic logging. It's designed to offload work from synchronous processes, such as API request handlers, to background workers.

## Features

-   **Asynchronous Processing**: Tasks are executed by `asyncio` workers, suitable for I/O-bound operations.
-   **Priority Queues**: Tasks can be assigned priorities, with lower numerical values indicating higher priority.
-   **Delayed Execution**: Tasks can be scheduled to run after a specified delay.
-   **In-Memory Broker**: The initial implementation includes an `InMemoryBroker` suitable for single-process applications and testing.
-   **Abstract Broker Design**: The `AbstractBroker` class defines an interface that allows for future expansion with other broker backends (e.g., Redis).
-   **Task State Management**: Tasks transition through states (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), which are tracked by the broker.
-   **Logging**: Key events in the task lifecycle (creation, processing, completion, failure) are logged.
-   **Graceful Shutdown**: Workers can be signaled to shut down gracefully.

## Core Components

1.  **`models.py`**:
    *   `TaskStatus` (Enum): Defines the possible states of a task (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`).
    *   `Task` (dataclass): Represents a task unit, containing its ID, name, priority, payload, scheduled time, creation time, and status.

2.  **`broker.py`**:
    *   `AbstractBroker` (ABC): Defines the interface for task brokers. Key methods include `enqueue`, `dequeue`, `get_task`, `update_task_status`, `mark_complete`, `mark_failed`.
    *   `InMemoryBroker`: An in-memory implementation of `AbstractBroker`. It uses `heapq` for managing task priorities and scheduled times. Suitable for single-process applications or testing.

3.  **`service.py`**:
    *   `TaskQueueService`: Orchestrates the task queue system.
        *   Manages a broker instance and a dictionary of `task_executors` (functions that know how to perform specific tasks).
        *   `add_task()`: Method to create and enqueue new tasks.
        *   `worker()`: The main loop for worker processes, which dequeue and execute tasks.
        *   `start_workers()`: Utility to launch multiple worker tasks.
        *   `shutdown()`: Method to signal workers to stop.
    *   `TaskExecutor` (Type Alias): Defines the signature for functions that execute tasks (`Callable[[Task], Coroutine[Any, Any, Any]]`).

## Usage

### 1. Define Task Executors

Task executors are `async` functions that take a `Task` object as input and perform the actual work.

```python
# In your application code (e.g., main.py or a dedicated tasks module)
import logging
from katana.task_queue.models import Task # Or from ..models if relative

logger = logging.getLogger(__name__)

async def my_email_task_executor(task: Task):
    logger.info(f"Sending email for task {task.id} with payload: {task.payload}")
    # Simulate sending email
    await asyncio.sleep(2)
    if "error" in task.payload:
        raise ValueError("Simulated email sending error")
    logger.info(f"Email sent for task {task.id}")

async def data_processing_executor(task: Task):
    logger.info(f"Processing data for task {task.id}: {task.payload.get('data_id')}")
    await asyncio.sleep(1)
    logger.info(f"Data processing complete for task {task.id}")

```

### 2. Initialize and Configure the Service

In your application's startup sequence (e.g., FastAPI `startup` event):

```python
# In main.py or similar
import asyncio
from katana.task_queue.broker import InMemoryBroker
from katana.task_queue.service import TaskQueueService
# Import your defined executors
# from .my_tasks import my_email_task_executor, data_processing_executor

# Global or application-scoped variables
task_queue_service: TaskQueueService = None
task_queue_worker_tasks: list = []

async def application_startup():
    global task_queue_service, task_queue_worker_tasks

    # 1. Define your task executors mapping
    # (Ensure executors are imported or defined in scope)
    registered_executors = {
        "send_email": my_email_task_executor, # Defined above
        "process_data": data_processing_executor, # Defined above
    }

    # 2. Initialize Broker
    broker = InMemoryBroker()

    # 3. Initialize Service
    task_queue_service = TaskQueueService(broker=broker, task_executors=registered_executors)

    # 4. Start Workers
    num_workers = 2 # Adjust as needed
    task_queue_worker_tasks = task_queue_service.start_workers(num_workers=num_workers)
    logger.info(f"Task queue service started with {num_workers} workers.")

    # ... other startup logic ...
```

### 3. Adding Tasks

Tasks can be added from anywhere in your application that has access to the `task_queue_service` instance.

```python
# Example: In a FastAPI endpoint or other service logic
async def some_api_endpoint_handler():
    # ...
    user_email = "user@example.com"
    email_content = "Your report is ready."

    if task_queue_service:
        try:
            await task_queue_service.add_task(
                name="send_email", # Must match a key in registered_executors
                payload={"to": user_email, "subject": "Report", "body": email_content},
                priority=1, # Lower is higher
                delay_seconds=5 # Optional: delay execution by 5 seconds
            )
            logger.info("Email task enqueued.")
        except ValueError as e: # e.g., if task name is not registered
            logger.error(f"Failed to enqueue task: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while enqueuing task: {e}")
    # ...
    return {"message": "Request accepted, processing in background."}
```

### 4. Graceful Shutdown

Ensure workers are shut down gracefully when your application exits.

```python
# In your application's shutdown sequence (e.g., FastAPI `shutdown` event)
async def application_shutdown():
    global task_queue_service, task_queue_worker_tasks

    if task_queue_service and task_queue_worker_tasks:
        logger.info("Shutting down task queue workers...")
        await task_queue_service.shutdown() # Signal workers
        try:
            await asyncio.gather(*task_queue_worker_tasks, return_exceptions=True)
            logger.info("All task queue workers have shut down.")
        except Exception as e:
            logger.error(f"Error during task queue worker shutdown: {e}")
    # ... other shutdown logic ...
```

## Testing

Unit tests for the task queue components are located in `tests/task_queue/test_task_queue.py`. These tests use `pytest` and `pytest-asyncio`.

To run tests:
```bash
# From the project root directory
# Ensure pytest and pytest-asyncio are installed
# pip install pytest pytest-asyncio

pytest tests/task_queue/
```

## Future Considerations

-   **Redis Broker**: Implement a `RedisBroker` for persistence, inter-process communication, and scalability.
-   **Task Result Handling**: Extend the system to store and retrieve results of completed tasks.
-   **Retries and Error Handling**: Implement more sophisticated retry mechanisms (e.g., exponential backoff) for failed tasks.
-   **Task Cancellation**: Add support for cancelling pending or processing tasks.
-   **Monitoring and Management API**: Expose more detailed metrics and control over the queue and workers via an API.
-   **Serialization**: For brokers like Redis, task payloads will need to be serialized (e.g., to JSON).

This module provides a foundational asynchronous task queue. The `main.py` in the root of this project includes a demonstration of its integration with a FastAPI application, including a debug endpoint `/debug/add_task` to manually enqueue tasks.
```
