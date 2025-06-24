import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple

@dataclass(order=True)
class Task:
    priority: int
    timestamp: float  # For tie-breaking and potential future use (e.g., TTL)
    task_id: uuid.UUID = field(compare=False)
    data: Any = field(compare=False)
    # Add item_id to ensure PriorityQueue can compare items if priority and timestamp are the same
    item_id: uuid.UUID = field(default_factory=uuid.uuid4, compare=True)


class TaskQueue:
    def __init__(
        self,
        on_task_received: Optional[Callable[[Task], None]] = None,
        on_task_done: Optional[Callable[[uuid.UUID], None]] = None,
        on_task_error: Optional[Callable[[uuid.UUID, Exception], None]] = None,
    ):
        self._queue = asyncio.PriorityQueue[Task]()
        self._on_task_received = on_task_received
        self._on_task_done = on_task_done
        self._on_task_error = on_task_error # This hook will be called by the worker

    async def add_task(
        self, data: Any, priority: int = 0, delay: Optional[float] = None
    ) -> uuid.UUID:
        """
        Adds a task to the queue.

        Args:
            data: The actual data payload of the task.
            priority: Integer representing task priority (lower is higher).
            delay: Optional delay in seconds before the task is actually added to the queue.

        Returns:
            The unique ID of the task.
        """
        task_id = uuid.uuid4()
        current_time = time.time()

        task = Task(priority=priority, timestamp=current_time, task_id=task_id, data=data)

        if delay and delay > 0:
            asyncio.create_task(self._add_task_after_delay(delay, task))
        else:
            await self._queue.put(task)
            if self._on_task_received:
                try:
                    self._on_task_received(task)
                except Exception as e:
                    # Log this error, as hook errors shouldn't stop queue logic
                    print(f"Error in on_task_received hook for task {task_id}: {e}")

        return task_id

    async def _add_task_after_delay(self, delay: float, task: Task):
        await asyncio.sleep(delay)
        await self._queue.put(task)
        if self._on_task_received:
            try:
                self._on_task_received(task)
            except Exception as e:
                # Log this error
                print(f"Error in on_task_received hook for task {task.task_id} after delay: {e}")

    async def get_task(self, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Retrieves the highest-priority task from the queue.

        Args:
            timeout: Optional maximum time in seconds to wait for a task.

        Returns:
            A Task object or None if timeout occurs.
        """
        try:
            if timeout is not None:
                task = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                task = await self._queue.get()
            return task
        except asyncio.TimeoutError:
            return None

    def acknowledge_task(self, task_id: uuid.UUID):
        """
        Acknowledges that a task has been completed successfully.
        Currently, this primarily triggers the on_task_done hook.
        """
        self._queue.task_done() # Notify the queue that the task is processed
        if self._on_task_done:
            try:
                self._on_task_done(task_id)
            except Exception as e:
                # Log this error
                print(f"Error in on_task_done hook for task {task_id}: {e}")

    # Method for workers to report errors.
    def report_task_error(self, task_id: uuid.UUID, error: Exception):
        """
        Reports an error that occurred while processing a task.
        This is intended to be called by the task consumer/worker.
        """
        if self._on_task_error:
            try:
                self._on_task_error(task_id, error)
            except Exception as e:
                # Log this error
                print(f"Error in on_task_error hook itself for task {task_id}: {e}")

    async def join(self):
        """Waits until all items in the queue have been received and processed."""
        await self._queue.join()

    def qsize(self) -> int:
        """Returns the approximate size of the queue."""
        return self._queue.qsize()

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise."""
        return self._queue.empty()

# Example Usage (can be removed or moved to a test/example file later)
async def example_worker(name: str, queue: TaskQueue):
    print(f"Worker {name} starting...")
    while True:
        print(f"Worker {name} waiting for task...")
        task = await queue.get_task()
        if task is None: # Should not happen with get_task without timeout unless queue is shut down.
            print(f"Worker {name} received None, stopping.")
            break

        print(f"Worker {name} received task {task.task_id} with priority {task.priority}: {task.data}")
        try:
            # Simulate work
            if task.data == "error_task":
                raise ValueError("Simulated processing error")
            await asyncio.sleep(1) # Simulate I/O bound work
            print(f"Worker {name} finished task {task.task_id}")
            queue.acknowledge_task(task.task_id)
        except Exception as e:
            print(f"Worker {name} failed task {task.task_id}: {e}")
            queue.report_task_error(task.task_id, e)
            # For asyncio.PriorityQueue, task_done() still needs to be called even on error
            # to unblock queue.join(). However, acknowledge_task already calls it.
            # If acknowledge_task was not called on error, we would need:
            # queue._queue.task_done()
            # For robustness, let's ensure task_done is called if not via acknowledge_task
            # However, current design implies acknowledge_task is for success.
            # The `task_done` call in `acknowledge_task` handles unblocking `join`.
            # If a task errors out and is NOT acknowledged, `join` might hang.
            # A common pattern is to always call task_done in a finally block in the worker.
            # Let's adjust: acknowledge_task is for success. A separate mechanism for task_done on error.
            # For now, let's assume the worker calls task_done() via acknowledge_task or directly.
            # The `acknowledge_task` already calls `task_done`.
            # If an error occurs, the worker *must* still ensure `task_done` is called on the underlying queue
            # or `join()` will block forever.
            # The simplest is that `get_task` is paired with a `try/finally` in the worker
            # that calls `queue._queue.task_done()`.
            # Let's refine this: `acknowledge_task` is for successful completion.
            # The worker should call `queue._queue.task_done()` regardless of outcome.

            # The current `acknowledge_task` calls `self._queue.task_done()`.
            # If a worker calls `report_task_error`, it should also ensure `task_done()` is called.
            # A good practice is for the worker to call `task_done()` in a `finally` clause.
            # So, let's assume the worker will call `_queue.task_done()`
            # For simplicity here, we can add a method like `task_processed`
            # Or, let's adjust `report_task_error` to also call task_done
            queue._queue.task_done() # Ensure task_done is called for error cases too.


async def main():
    # --- Hook Examples ---
    def my_on_received(task: Task):
        print(f"[Hook] Task received: {task.task_id} - {task.data}")

    def my_on_done(task_id: uuid.UUID):
        print(f"[Hook] Task done: {task_id}")

    def my_on_error(task_id: uuid.UUID, error: Exception):
        print(f"[Hook] Task error: {task_id} - {error}")
    # --- End Hook Examples ---

    task_queue = TaskQueue(
        on_task_received=my_on_received,
        on_task_done=my_on_done,
        on_task_error=my_on_error
    )

    # Start workers
    worker1 = asyncio.create_task(example_worker("Worker-1", task_queue))
    # worker2 = asyncio.create_task(example_worker("Worker-2", task_queue))

    # Add tasks
    await task_queue.add_task("Task A (High Prio)", priority=0)
    await task_queue.add_task("Task B (Low Prio)", priority=10)
    await task_queue.add_task("Task C (Delayed 2s, Mid Prio)", priority=5, delay=2)
    await task_queue.add_task("Task D (High Prio)", priority=0)
    task_id_error = await task_queue.add_task("error_task", priority=1)
    print(f"Added error task with ID: {task_id_error}")
    await task_queue.add_task("Task E (After Error, Prio 2)", priority=2)


    # Wait for a bit for tasks to be processed by workers
    # In a real app, you'd manage worker lifecycle more robustly.
    print("Waiting for tasks to be added to queue (especially delayed ones)...")
    await asyncio.sleep(3) # Allow delayed task to be added

    print(f"Queue size approx: {task_queue.qsize()}")

    # Wait for all tasks to be processed by calling queue.join()
    # This requires workers to call task_done() for every task they get.
    print("Waiting for all tasks to be processed...")
    await task_queue.join()
    print("All tasks processed.")

    # Cancel workers (important for clean shutdown)
    worker1.cancel()
    # worker2.cancel()
    try:
        await worker1
    except asyncio.CancelledError:
        print("Worker-1 was cancelled.")
    # try:
    #     await worker2
    # except asyncio.CancelledError:
    #     print("Worker-2 was cancelled.")

    print("Example finished.")

if __name__ == "__main__":
    # Note: The example usage needs to be run in an asyncio event loop.
    # You would typically run this with `python -m katana.core.task_queue` if you want to execute the example.
    # For now, this if __name__ == "__main__": block is for clarity.
    # To run:
    # import asyncio
    # from katana.core.task_queue import main as run_main # Assuming file is saved as task_queue.py
    # asyncio.run(run_main())
    pass
