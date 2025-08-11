import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, Optional, List

from katana.task_queue.broker import AbstractBroker
from katana.task_queue.models import Task, TaskStatus

# Configure basic logging for the service
logger = logging.getLogger(__name__)
# Example basic config (ideally, this is configured globally in the application)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Type alias for an async task executor function
# It takes a Task object and returns an arbitrary result (or None)
TaskExecutor = Callable[[Task], Coroutine[Any, Any, Any]]


class TaskQueueService:
    def __init__(self, broker: AbstractBroker, task_executors: Dict[str, TaskExecutor]):
        """
        Initializes the Task Queue Service.

        Args:
            broker: An instance of a class that implements AbstractBroker.
            task_executors: A dictionary mapping task names (str) to
                            async functions (TaskExecutor) that know how to execute those tasks.
                            Example: {"send_email": async_send_email_function}
        """
        if not isinstance(broker, AbstractBroker):
            raise TypeError("broker must be an instance of AbstractBroker")
        if not isinstance(task_executors, dict) or not all(
            isinstance(k, str) and callable(v) for k, v in task_executors.items()
        ):
            raise TypeError(
                "task_executors must be a dictionary of string keys to callable async functions."
            )

        self.broker = broker
        self.task_executors = task_executors
        self._stop_event = asyncio.Event()  # Used to signal workers to stop

    async def add_task(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: int = 0,  # Lower is higher priority
        delay_seconds: Optional[float] = None,
        task_id: Optional[
            uuid.UUID
        ] = None,  # Allow specifying ID for idempotent retries etc.
    ) -> Task:
        """
        Creates a new task and adds it to the broker.

        Args:
            name: The name of the task, which should correspond to a key in `task_executors`.
            payload: A dictionary containing data required for the task.
            priority: Integer priority, lower values are processed first.
            delay_seconds: Optional delay in seconds before the task should be scheduled.
            task_id: Optional UUID for the task. If None, a new one is generated.

        Returns:
            The created Task object.

        Raises:
            ValueError: If the task name is not found in task_executors.
        """
        if name not in self.task_executors:
            logger.error(f"Task name '{name}' not found in registered task executors.")
            raise ValueError(
                f"Task name '{name}' not found in registered task executors."
            )

        now = datetime.now(timezone.utc)
        scheduled_at = now
        if delay_seconds is not None:
            if delay_seconds < 0:
                raise ValueError("delay_seconds cannot be negative.")
            scheduled_at = now + timedelta(seconds=delay_seconds)

        task = Task(
            id=task_id if task_id else uuid.uuid4(),
            name=name,
            payload=payload,
            priority=priority,
            scheduled_at=scheduled_at,
            created_at=now,  # Will be set by default_factory if not passed, but good to be explicit
            status=TaskStatus.PENDING,
        )

        await self.broker.enqueue(task)
        logger.info(
            f"Task {task.id} (Name: {task.name}, Priority: {task.priority}, Scheduled: {task.scheduled_at}) enqueued."
        )
        return task

    async def _execute_task(self, task: Task) -> None:
        """
        Internal method to execute a single task.
        It calls the appropriate executor based on task.name.
        """
        executor = self.task_executors.get(task.name)
        if not executor:
            logger.error(
                f"No executor found for task name '{task.name}' (ID: {task.id}). Marking as FAILED."
            )
            await self.broker.mark_failed(task.id)
            return

        logger.info(f"Starting execution of task {task.id} (Name: {task.name}).")
        try:
            # The executor function is responsible for its own logic
            result = await executor(task)
            await self.broker.complete_task(task.id, result=result)
            logger.info(
                f"Task {task.id} (Name: {task.name}) completed successfully with result: {result}"
            )
        except Exception as e:
            logger.error(
                f"Error executing task {task.id} (Name: {task.name}): {e}",
                exc_info=True,
            )
            await self.broker.mark_failed(task.id)
            # Optionally, implement retry logic here or in the broker/executor

    async def worker(self, worker_id: int, poll_interval: float = 0.1) -> None:
        """
        A worker process that continuously fetches and executes tasks.

        Args:
            worker_id: An identifier for this worker (for logging).
            poll_interval: Time in seconds to wait before polling for new tasks if queue is empty or tasks are not due.
        """
        logger.info(f"Worker {worker_id} starting.")
        while not self._stop_event.is_set():
            task_to_process = None
            try:
                dequeued_task = await self.broker.dequeue()

                if dequeued_task:
                    # Double check status, as it might have been changed by another process
                    # if the broker doesn't atomically mark it as PROCESSING on dequeue.
                    # Our InMemoryBroker returns it as PENDING.
                    current_task_state = await self.broker.get_task(dequeued_task.id)
                    if (
                        current_task_state
                        and current_task_state.status == TaskStatus.PENDING
                    ):
                        # Atomically (as much as possible for in-mem) set to PROCESSING
                        # This prevents other workers from picking up the same PENDING task
                        # if dequeue itself doesn't change status.
                        # A more robust broker (e.g., Redis) would handle this atomically.
                        # For InMemoryBroker, the lock in update_task_status helps.
                        updated = await self.broker.update_task_status(
                            dequeued_task.id, TaskStatus.PROCESSING
                        )
                        if updated:
                            task_to_process = await self.broker.get_task(
                                dequeued_task.id
                            )  # Get the version with PROCESSING status
                            logger.info(
                                f"Worker {worker_id} picked up task {task_to_process.id} (Name: {task_to_process.name})."
                            )
                        else:
                            logger.warning(
                                f"Worker {worker_id}: Failed to update task {dequeued_task.id} to PROCESSING. It might have been processed or changed by another worker."
                            )
                            continue  # Try to get another task
                    elif current_task_state:
                        logger.info(
                            f"Worker {worker_id}: Dequeued task {dequeued_task.id} but its status is {current_task_state.status}. Skipping."
                        )
                        continue
                    else:
                        logger.warning(
                            f"Worker {worker_id}: Dequeued task ID {dequeued_task.id} but task data not found in broker. Skipping."
                        )
                        continue

                if task_to_process and task_to_process.status == TaskStatus.PROCESSING:
                    await self._execute_task(task_to_process)
                else:
                    # No task due, or dequeue returned None
                    await asyncio.sleep(poll_interval)  # Wait before polling again

            except asyncio.CancelledError:
                logger.info(
                    f"Worker {worker_id} received cancellation request. Shutting down..."
                )
                break  # Exit the loop if the task is cancelled
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} encountered an unexpected error: {e}",
                    exc_info=True,
                )
                # Sleep for a bit to avoid rapid-fire errors in case of persistent issues
                await asyncio.sleep(poll_interval * 5)

        logger.info(f"Worker {worker_id} stopped.")

    def start_workers(
        self, num_workers: int, poll_interval: float = 0.1
    ) -> List[asyncio.Task]:
        """
        Starts a specified number of worker tasks.
        """
        if num_workers <= 0:
            raise ValueError("Number of workers must be positive.")

        self._stop_event.clear()  # Ensure stop event is clear before starting
        worker_tasks = []
        for i in range(num_workers):
            # Create task for each worker
            task = asyncio.create_task(
                self.worker(worker_id=i + 1, poll_interval=poll_interval)
            )
            worker_tasks.append(task)
        logger.info(f"Started {num_workers} worker(s).")
        return worker_tasks

    async def shutdown(self) -> None:
        """
        Signals all workers to stop and waits for them to finish.
        This should be called when the application is shutting down.
        """
        logger.info("TaskQueueService shutdown initiated. Signaling workers to stop...")
        self._stop_event.set()
        # Workers will check this event and exit their loops.
        # If workers are currently processing a task, they will finish it first (unless _execute_task is made cancellable).
        # For a graceful shutdown, you might want to await the worker tasks if they are stored.
        # The `start_workers` returns the tasks, so the caller can await them.
        logger.info(
            "Shutdown signal sent. Workers will stop after their current task or next poll."
        )


# Example Task Executor Functions (to be defined by the user of the service)
async def example_task_executor_log(task: Task):
    logger.info(
        f"Executing example_task_executor_log for task {task.id}: Name='{task.name}', Payload='{task.payload}'"
    )
    # Simulate work
    await asyncio.sleep(1)
    if task.payload.get("force_fail", False):
        raise ValueError("Forced failure for testing.")
    logger.info(f"Finished example_task_executor_log for task {task.id}")


async def another_example_executor(task: Task):
    logger.info(
        f"Executing another_example_executor for task {task.id}: Name='{task.name}', Payload='{task.payload}'"
    )
    await asyncio.sleep(0.5)
    logger.info(f"Finished another_example_executor for task {task.id}")


# Example of how to use the TaskQueueService (e.g., in your main application file)
async def main_service_example():
    # Configure logging (if not done globally)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - [%(threadName)s] - %(message)s",
    )

    # 1. Setup Broker
    from katana.task_queue.broker import (
        InMemoryBroker,
    )  # Assuming this is in the same directory for example

    broker = InMemoryBroker()

    # 2. Define your task executor functions (like example_task_executor_log above)
    registered_executors = {
        "log_message": example_task_executor_log,
        "short_work": another_example_executor,
    }

    # 3. Initialize Service
    service = TaskQueueService(broker=broker, task_executors=registered_executors)

    # 4. Start Workers (in background)
    num_workers = 2
    worker_tasks = service.start_workers(num_workers=num_workers, poll_interval=0.2)

    # 5. Add some tasks
    task1 = await service.add_task(
        name="log_message",
        payload={"message": "Hello from Task 1", "user_id": 123},
        priority=1,
    )
    task2 = await service.add_task(
        name="short_work", payload={"data": "Some data for short work"}, priority=0
    )
    task3 = await service.add_task(
        name="log_message",
        payload={"message": "Delayed critical task", "critical": True},
        priority=0,
        delay_seconds=3,
    )
    task4_fail = await service.add_task(
        name="log_message",
        payload={"message": "This task will fail", "force_fail": True},
        priority=2,
    )

    # Add a task that doesn't have an executor
    try:
        await service.add_task(name="non_existent_task", payload={"data": "test"})
    except ValueError as e:
        logger.error(f"Error adding task: {e}")

    # Let workers run for a bit
    await asyncio.sleep(5)  # Enough time for initial tasks + delayed task

    # Add more tasks while workers are running
    await service.add_task(
        name="short_work", payload={"data": "Another short work"}, priority=1
    )
    await service.add_task(
        name="log_message", payload={"message": "Low priority task"}, priority=10
    )

    # Let it run a bit more
    await asyncio.sleep(5)

    # 6. Shutdown
    logger.info("Main example: Initiating service shutdown...")
    await service.shutdown()

    # Wait for all worker tasks to complete
    # Add timeout to prevent hanging indefinitely if a worker doesn't stop
    try:
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        logger.info("Main example: All workers have shut down.")
    except asyncio.TimeoutError:
        logger.error("Main example: Timeout waiting for workers to shut down.")
    except Exception as e:
        logger.error(f"Main example: Error during worker shutdown: {e}", exc_info=True)

    # Verify task statuses (optional, for demonstration)
    logger.info("\nFinal Task Statuses:")
    for task_obj in [
        task1,
        task2,
        task3,
        task4_fail,
    ]:  # Add newly added tasks if you want to check them
        final_status_task = await broker.get_task(task_obj.id)
        if final_status_task:
            logger.info(
                f"Task {final_status_task.name} (ID: {final_status_task.id}): {final_status_task.status}"
            )
        else:
            logger.info(f"Task ID {task_obj.id} not found in broker (unexpected).")

    # Check a task that was added later
    task5_check = await broker.get_task(
        (await broker.dequeue()).id
    )  # This is a bit of a hack to get a recent task ID
    # A better way would be to store the returned task object
    # This dequeue might get nothing if queue is empty. A more robust check needed if we care.
    # For now, this is just for rough verification in example.
    # A better way: Store all returned tasks from add_task in a list and iterate.


if __name__ == "__main__":
    # To run this example:
    # Ensure katana.task_queue.broker and katana.task_queue.models are accessible.
    # This might require adjusting PYTHONPATH or running from the project root.
    # Example: python -m katana.task_queue.service
    # asyncio.run(main_service_example())
    # Commented out direct run as it's usually part of a larger app.
    pass
