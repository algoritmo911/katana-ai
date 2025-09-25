import asyncio
import logging
import uuid
import dill
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine, Dict, Optional, List

from katana.task_queue.broker import AbstractBroker
from katana.task_queue.models import Task, TaskStatus

# Configure basic logging for the service
logger = logging.getLogger(__name__)

# Type alias for an async task executor function
TaskExecutor = Callable[[Task], Coroutine[Any, Any, Any]]


async def execute_pickled_task(task: Task) -> Any:
    """
    A generic task executor that deserializes and runs a pickled function.
    """
    logger.info(f"Executing pickled task {task.id}")
    try:
        func, args, kwargs = dill.loads(task.payload["task_data"])
        logger.info(f"Deserialized task: {func.__name__}")
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            # To avoid blocking the worker, run sync functions in a thread pool
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing pickled task {task.id}: {e}", exc_info=True)
        raise


class TaskQueueService:
    def __init__(self, broker: AbstractBroker, task_executors: Dict[str, TaskExecutor]):
        if not isinstance(broker, AbstractBroker):
            raise TypeError("broker must be an instance of AbstractBroker")

        # Make a copy to avoid modifying the original dict
        self.task_executors = task_executors.copy()
        # Add the generic executor for pickled tasks
        self.task_executors["execute_pickled_task"] = execute_pickled_task

        if not all(isinstance(k, str) and callable(v) for k, v in self.task_executors.items()):
            raise TypeError(
                "task_executors must be a dictionary of string keys to callable async functions."
            )

        self.broker = broker
        self._stop_event = asyncio.Event()  # Used to signal workers to stop

    async def add_task_to_queue(self, task_function: Callable, *args, **kwargs) -> Task:
        """
        Adds any function and its arguments to the queue for background execution.
        """
        if not callable(task_function):
            raise TypeError("task_function must be a callable function.")

        task_data = dill.dumps((task_function, args, kwargs))

        now = datetime.now(timezone.utc)
        task = Task(
            name="execute_pickled_task",
            payload={"task_data": task_data},
            priority=0,
            scheduled_at=now,
            created_at=now,
        )

        await self.broker.enqueue(task)
        logger.info(
            f"Task {task.id} (Name: {task.name}, Priority: {task.priority}, Scheduled: {task.scheduled_at}) enqueued."
        )
        return task


    async def _execute_task(self, task: Task) -> None:
        executor = self.task_executors.get(task.name)
        if not executor:
            logger.error(
                f"No executor found for task name '{task.name}' (ID: {task.id}). Marking as FAILED."
            )
            await self.broker.mark_failed(task.id)
            return

        logger.info(f"Starting execution of task {task.id} (Name: {task.name}).")
        try:
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

    async def worker(self, worker_id: int, poll_interval: float = 0.1) -> None:
        logger.info(f"Worker {worker_id} starting.")
        while not self._stop_event.is_set():
            task_to_process = None
            try:
                dequeued_task = await self.broker.dequeue()

                if dequeued_task:
                    current_task_state = await self.broker.get_task(dequeued_task.id)
                    if (
                        current_task_state
                        and current_task_state.status == TaskStatus.PENDING
                    ):
                        updated = await self.broker.update_task_status(
                            dequeued_task.id, TaskStatus.PROCESSING
                        )
                        if updated:
                            task_to_process = await self.broker.get_task(
                                dequeued_task.id
                            )
                            logger.info(
                                f"Worker {worker_id} picked up task {task_to_process.id} (Name: {task_to_process.name})."
                            )
                        else:
                            logger.warning(
                                f"Worker {worker_id}: Failed to update task {dequeued_task.id} to PROCESSING. It might have been processed or changed by another worker."
                            )
                            continue
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
                    await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info(
                    f"Worker {worker_id} received cancellation request. Shutting down..."
                )
                break
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} encountered an unexpected error: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(poll_interval * 5)

        logger.info(f"Worker {worker_id} stopped.")

    def start_workers(
        self, num_workers: int, poll_interval: float = 0.1
    ) -> List[asyncio.Task]:
        if num_workers <= 0:
            raise ValueError("Number of workers must be positive.")

        self._stop_event.clear()
        worker_tasks = []
        for i in range(num_workers):
            task = asyncio.create_task(
                self.worker(worker_id=i + 1, poll_interval=poll_interval)
            )
            worker_tasks.append(task)
        logger.info(f"Started {num_workers} worker(s).")
        return worker_tasks

    async def get_task_status(self, task_id: uuid.UUID) -> Optional[TaskStatus]:
        """
        Retrieves the status of a task by its ID.
        """
        task = await self.broker.get_task(task_id)
        return task.status if task else None

    async def shutdown(self) -> None:
        logger.info("TaskQueueService shutdown initiated. Signaling workers to stop...")
        self._stop_event.set()
        logger.info(
            "Shutdown signal sent. Workers will stop after their current task or next poll."
        )
