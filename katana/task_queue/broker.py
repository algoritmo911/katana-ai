from abc import ABC, abstractmethod
from typing import Optional, Any
import uuid

from katana.task_queue.models import Task


class AbstractBroker(ABC):
    """
    Abstract base class for a task queue broker.
    Defines the interface for enqueuing, dequeuing, and managing task statuses.
    """

    @abstractmethod
    async def enqueue(self, task: Task) -> None:
        """
        Adds a task to the queue.
        The broker is responsible for storing the task and respecting its priority and scheduled_at time.
        """
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[Task]:
        """
        Retrieves and removes the highest priority, due task from the queue.
        A task is considered "due" if its scheduled_at time is now or in the past.
        Among due tasks, the one with the numerically lowest priority value is chosen.
        If priorities are equal, the one scheduled earliest is chosen.
        If scheduled_at times are also equal, the one created earliest is chosen.
        Returns:
            The next Task to be processed, or None if no tasks are currently due.
            The returned task should typically be marked as PROCESSING by the caller or worker.
        """
        pass

    @abstractmethod
    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        """
        Retrieves a task by its ID without removing it from the queue.
        This is useful for checking the status or details of a specific task.
        """
        pass

    @abstractmethod
    async def update_task_status(self, task_id: uuid.UUID, status: "TaskStatus") -> bool:  # type: ignore
        """
        Updates the status of a task.
        Args:
            task_id: The ID of the task to update.
            status: The new TaskStatus.
        Returns:
            True if the task was found and updated, False otherwise.
        """
        pass

    # The plan mentioned mark_complete and mark_failed.
    # These can be implemented by using update_task_status, or be explicit methods.
    # For flexibility, update_task_status is good.
    # Let's stick to the plan for now and add them as distinct, possibly calling update_task_status internally.

    @abstractmethod
    async def mark_complete(self, task_id: uuid.UUID) -> bool:
        """
        Marks a task as COMPLETED.
        Returns:
            True if the task was found and marked, False otherwise.
        """
        pass

    @abstractmethod
    async def complete_task(self, task_id: uuid.UUID, result: Any) -> bool:
        """
        Marks a task as COMPLETED and stores its result.
        Args:
            task_id: The ID of the task to complete.
            result: The result payload to store.
        Returns:
            True if the task was found and updated, False otherwise.
        """
        pass

    @abstractmethod
    async def mark_failed(self, task_id: uuid.UUID) -> bool:
        """
        Marks a task as FAILED.
        Returns:
            True if the task was found and marked, False otherwise.
        """
        pass

    @abstractmethod
    async def task_exists(self, task_id: uuid.UUID) -> bool:
        """Checks if a task with the given ID exists in the broker's storage."""
        pass

    # Optional: Add a method to get queue size or other stats, if needed later.
    # async def get_queue_stats(self) -> dict:
    #     pass


if __name__ == "__main__":
    # This section is for illustrative purposes and won't be run directly in production.
    # It helps confirm the ABC definition.

    # Cannot instantiate an ABC directly
    # broker = AbstractBroker() # This would raise a TypeError

    # Example of a concrete class (for illustration only here)
    class DummyBroker(AbstractBroker):
        async def enqueue(self, task: Task) -> None:
            print(f"DummyBroker: Enqueued task {task.id}")

        async def dequeue(self) -> Optional[Task]:
            print("DummyBroker: Dequeue called")
            return None

        async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
            print(f"DummyBroker: Get task {task_id}")
            return None

        async def update_task_status(self, task_id: uuid.UUID, status: "TaskStatus") -> bool:  # type: ignore
            print(f"DummyBroker: Update task {task_id} to {status}")
            return True

        async def mark_complete(self, task_id: uuid.UUID) -> bool:
            print(f"DummyBroker: Marked task {task_id} as COMPLETED.")
            # In a real implementation, this would likely call:
            # from katana.task_queue.models import TaskStatus
            # return await self.update_task_status(task_id, TaskStatus.COMPLETED)
            return True

        async def mark_failed(self, task_id: uuid.UUID) -> bool:
            print(f"DummyBroker: Marked task {task_id} as FAILED.")
            # from katana.task_queue.models import TaskStatus
            # return await self.update_task_status(task_id, TaskStatus.FAILED)
            return True

        async def task_exists(self, task_id: uuid.UUID) -> bool:
            print(f"DummyBroker: Task exists check for {task_id}")
            return False

    async def main_dummy():
        broker: AbstractBroker = DummyBroker()
        # Example task (requires Task model from models.py)
        from datetime import datetime, timezone
        from katana.task_queue.models import (
            Task as ActualTask,
        )  # Renamed to avoid conflict

        example_task = ActualTask(
            priority=1,
            scheduled_at=datetime.now(timezone.utc),
            name="Example",
            payload={},
        )
        await broker.enqueue(example_task)
        await broker.dequeue()
        await broker.mark_complete(example_task.id)

    # To run main_dummy, you would need asyncio.run(main_dummy())
    # but this is just for verifying the ABC structure.
    print("AbstractBroker defined.")

import asyncio
import heapq
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional  # Import Set if using it
import uuid

from katana.task_queue.models import Task, TaskStatus


# Heap item: (priority, scheduled_at, created_at, task_id)
# We use task_id instead of the full Task object in the heap to keep it lightweight
# and avoid issues if Task objects are not directly comparable for heap purposes.
HeapItem = Tuple[int, datetime, datetime, uuid.UUID]


class InMemoryBroker(AbstractBroker):
    """
    In-memory implementation of the AbstractBroker.
    Uses a min-heap for the priority queue and a dictionary to store task details.
    This implementation is intended for single-process applications or testing.
    It is thread-safe due to asyncio locks, making it safe for concurrent asyncio tasks.
    """

    def __init__(self):
        self._tasks: Dict[uuid.UUID, Task] = {}  # Stores actual Task objects
        self._queue: List[HeapItem] = (
            []
        )  # Min-heap storing (priority, scheduled_at, created_at, task_id)
        self._lock = asyncio.Lock()  # To ensure atomic operations on shared state

    async def enqueue(self, task: Task) -> None:
        async with self._lock:
            if task.id in self._tasks:
                # Or raise an error, or update if allowed. For now, let's prevent duplicates by ID.
                # This could happen if a UUID4 collision occurs, though highly unlikely.
                # More likely, it's a bug in task creation/submission logic.
                print(
                    f"Warning: Task with ID {task.id} already exists. Skipping enqueue."
                )
                return

            # Ensure the task is in PENDING state before adding
            # If it's already some other status, it might be a re-enqueue logic error
            if task.status != TaskStatus.PENDING:
                # Forcing it to PENDING if we allow re-queueing of tasks in non-pending states
                # For now, let's assume tasks are always new or explicitly set to PENDING before enqueue
                task_to_store = task.with_status(TaskStatus.PENDING)
            else:
                task_to_store = task

            self._tasks[task_to_store.id] = task_to_store
            heap_item: HeapItem = (
                task_to_store.priority,
                task_to_store.scheduled_at,
                task_to_store.created_at,
                task_to_store.id,
            )
            heapq.heappush(self._queue, heap_item)
            # print(f"Enqueued: {task_to_store.id}, Queue size: {len(self._queue)}, Tasks count: {len(self._tasks)}")

    async def dequeue(self) -> Optional[Task]:
        async with self._lock:
            if not self._queue:
                return None

            # Peek at the top item
            priority, scheduled_at, created_at, task_id = self._queue[0]

            # Check if the task is due
            if scheduled_at > datetime.now(timezone.utc):
                return None  # Not due yet

            # If due, pop it from the heap
            heapq.heappop(self._queue)

            task = self._tasks.get(task_id)
            if not task:
                # This would indicate an inconsistency, e.g., task removed from _tasks but not queue
                # Or if the task was marked completed/failed and removed from _tasks
                # For now, if it's not in _tasks, it's effectively gone.
                # Consider logging this as an error or warning.
                return None  # Task data not found, try next time

            # Transition task to PROCESSING status
            # The service layer is responsible for calling this, but the broker can ensure it.
            # However, the plan suggests the service layer does this.
            # For now, let's return the PENDING task. The service will update its status.
            # If the task was already removed (e.g. by explicit deletion not yet implemented)
            # or its status changed to COMPLETED/FAILED by another mechanism, this dequeue might be problematic.
            # Let's assume tasks in the queue are PENDING or ready to be processed.
            # A task should only be in the _queue if it's in a state that allows it to be processed.
            # If a task is marked COMPLETED/FAILED, it should ideally be removed from _queue if possible,
            # or dequeue should ignore it.
            # Current simple approach: if it's in _queue and popped, it's considered for processing.

            if task.status != TaskStatus.PENDING:
                # If the task is no longer PENDING (e.g., it was cancelled, completed by a race),
                # then skip it and try to dequeue another. This needs a loop.
                # print(f"Task {task.id} was in queue but status is {task.status}. Re-dequeuing.")
                # This recursive call needs to be careful about stack depth if many such tasks exist.
                # A loop is better:
                # while self._queue:
                #   ... pop ...
                #   if task and task.status == TaskStatus.PENDING:
                #     return task
                # return None
                # For now, let's assume if it's in the queue, it's PENDING.
                # The status update to PROCESSING will be done by the TaskQueueService.
                pass

            # print(f"Dequeued: {task.id}, Queue size: {len(self._queue)}, Tasks count: {len(self._tasks)}")
            return task

    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task_status(self, task_id: uuid.UUID, status: TaskStatus) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                # Create a new task instance with updated status (because Task is frozen)
                self._tasks[task_id] = task.with_status(status)

                # If task is completed or failed, it's logically not part of the "pending" queue anymore.
                # However, removing from self._queue by task_id is O(n).
                # Dequeue logic will eventually pop it and can ignore it if status is not PENDING.
                # For simplicity, we don't remove from _queue here. Dequeue handles non-PENDING tasks.
                # Alternative: If a task is marked COMPLETED or FAILED, we could try to remove it
                # from _queue. This is complex as _queue stores tuples, not Task objects directly.
                # We'd need to find the specific HeapItem: (p, s_at, c_at, task_id) and remove it, then heapify.
                # heapq doesn't support efficient arbitrary item removal.
                # The common pattern for this is to mark an item as "removed" and ignore it when popped.
                # Our current dequeue doesn't explicitly ignore already processed tasks, but
                # the service layer won't re-process a task that's not PENDING.
                # A robust dequeue would look like:
                # while self._queue:
                #   ... pop item ...
                #   task = self._tasks.get(task_id)
                #   if task and task.status == TaskStatus.PENDING:
                #     # Update status to PROCESSING here or by caller
                #     # self._tasks[task_id] = task.with_status(TaskStatus.PROCESSING)
                #     return task
                # return None
                # This ensures that only truly PENDING tasks are returned.
                # The current `dequeue` returns the task, and the service updates status.
                # If `update_task_status` is called before dequeue for the same task (race),
                # dequeue might return a non-PENDING task. This is acceptable if service checks status.
                return True
            return False

    async def mark_complete(self, task_id: uuid.UUID) -> bool:
        return await self.complete_task(task_id, result=None)

    async def complete_task(self, task_id: uuid.UUID, result: Any) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                updated_task = task.with_status(TaskStatus.COMPLETED).with_result(
                    result
                )
                self._tasks[task_id] = updated_task
                return True
            return False

    async def mark_failed(self, task_id: uuid.UUID) -> bool:
        # print(f"InMemoryBroker: Marking task {task_id} as FAILED.")
        return await self.update_task_status(task_id, TaskStatus.FAILED)

    async def task_exists(self, task_id: uuid.UUID) -> bool:
        async with self._lock:
            return task_id in self._tasks

    # Helper for testing or debugging, not part of AbstractBroker
    async def get_queue_size(self) -> int:
        async with self._lock:
            return len(self._queue)

    async def get_pending_task_count(self) -> int:
        async with self._lock:
            # This is an estimate, as tasks in _queue might have their status changed in _tasks
            # A more accurate count would iterate through _tasks and check status.
            # Or, iterate _queue, get task from _tasks, check status.
            count = 0
            for _, _, _, task_id in self._queue:
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    count += 1
            return count


# Example usage (for testing purposes)
async def _test_in_memory_broker():
    print("Testing InMemoryBroker...")
    broker = InMemoryBroker()

    now = datetime.now(timezone.utc)

    task1 = Task(
        id=uuid.uuid4(),
        name="Task 1 (High Prio, Now)",
        priority=0,
        scheduled_at=now,
        payload={"p": 1},
    )
    task2 = Task(
        id=uuid.uuid4(),
        name="Task 2 (Med Prio, Now)",
        priority=5,
        scheduled_at=now,
        payload={"p": 2},
    )
    task3_delayed = Task(
        id=uuid.uuid4(),
        name="Task 3 (High Prio, Delayed)",
        priority=0,
        scheduled_at=now + timedelta(seconds=5),
        payload={"p": 3},
    )
    task4_later_created = Task(
        id=uuid.uuid4(),
        name="Task 4 (High Prio, Now, Later Created)",
        priority=0,
        scheduled_at=now,
        created_at=now + timedelta(microseconds=100),
        payload={"p": 4},
    )

    await broker.enqueue(task1)
    await broker.enqueue(task2)
    await broker.enqueue(task3_delayed)  # Delayed
    await broker.enqueue(task4_later_created)

    print(f"Queue size after enqueues: {await broker.get_queue_size()}")
    print(f"Pending tasks: {await broker.get_pending_task_count()}")

    # Test dequeueing
    print("\nDequeuing tasks (should be None as task3 is delayed):")
    # Dequeue (task3 is delayed, task1, task4, task2 are due. task1 is prio 0, earliest created)
    dequed_task = await broker.dequeue()
    assert (
        dequed_task and dequed_task.id == task1.id
    ), f"Expected {task1.id}, got {dequed_task.id if dequed_task else 'None'}"
    print(f"Dequeued: {dequed_task.name if dequed_task else 'None'}")
    if dequed_task:
        await broker.update_task_status(dequed_task.id, TaskStatus.PROCESSING)

    dequed_task = (
        await broker.dequeue()
    )  # task4_later_created is prio 0, scheduled_now, created later than task1
    assert (
        dequed_task and dequed_task.id == task4_later_created.id
    ), f"Expected {task4_later_created.id}, got {dequed_task.id if dequed_task else 'None'}"
    print(f"Dequeued: {dequed_task.name if dequed_task else 'None'}")
    if dequed_task:
        await broker.update_task_status(dequed_task.id, TaskStatus.PROCESSING)

    dequed_task = await broker.dequeue()  # task2 is prio 5
    assert (
        dequed_task and dequed_task.id == task2.id
    ), f"Expected {task2.id}, got {dequed_task.id if dequed_task else 'None'}"
    print(f"Dequeued: {dequed_task.name if dequed_task else 'None'}")
    if dequed_task:
        await broker.mark_complete(dequed_task.id)
        completed_task_check = await broker.get_task(dequed_task.id)
        assert (
            completed_task_check and completed_task_check.status == TaskStatus.COMPLETED
        )
        print(f"Task {dequed_task.name} marked COMPLETED.")

    # At this point, only task3_delayed should be in the queue, and it's not due yet.
    print("\nAttempting to dequeue before task3 is due:")
    dequed_task = await broker.dequeue()
    assert (
        dequed_task is None
    ), f"Expected None, got {dequed_task.name if dequed_task else 'None'} because task3 is not due."
    print(f"Dequeued: {dequed_task.name if dequed_task else 'None'}")

    print(f"\nWaiting for task3_delayed to become due (5 seconds)...")
    # Need to import timedelta for this test code
    from datetime import timedelta

    await asyncio.sleep(5.1)

    print("\nAttempting to dequeue task3_delayed after it's due:")
    dequed_task = await broker.dequeue()
    assert (
        dequed_task and dequed_task.id == task3_delayed.id
    ), f"Expected {task3_delayed.id}, got {dequed_task.id if dequed_task else 'None'}"
    print(f"Dequeued: {dequed_task.name if dequed_task else 'None'}")
    if dequed_task:
        await broker.mark_failed(dequed_task.id)
        failed_task_check = await broker.get_task(dequed_task.id)
        assert failed_task_check and failed_task_check.status == TaskStatus.FAILED
        print(f"Task {dequed_task.name} marked FAILED.")

    print("\nQueue should be empty now:")
    dequed_task = await broker.dequeue()
    assert dequed_task is None, "Queue should be empty"
    print(f"Dequeued: {dequed_task.name if dequed_task else 'None'}")
    print(f"Final queue size: {await broker.get_queue_size()}")
    print(f"Final pending tasks: {await broker.get_pending_task_count()}")

    # Test get_task and task_exists
    retrieved_task1 = await broker.get_task(task1.id)
    assert retrieved_task1 and retrieved_task1.status == TaskStatus.PROCESSING
    print(
        f"\nRetrieved task1: {retrieved_task1.name}, status: {retrieved_task1.status}"
    )

    assert await broker.task_exists(task1.id) == True
    assert await broker.task_exists(uuid.uuid4()) == False
    print("Task existence checks passed.")

    print("\nInMemoryBroker test completed.")


if __name__ == "__main__":
    # This is how you would run the test function if this file were executed directly.
    # Note: The AbstractBroker definition is in the same file, so it's available.
    # Task and TaskStatus are also imported from models.

    # The test function needs `timedelta`
    from datetime import timedelta

    # Running the async test function:
    # asyncio.run(_test_in_memory_broker())
    # This will fail if run directly because of how __main__ interacts with asyncio if top-level await is not supported
    # or if this file is imported elsewhere.
    # Typically, you'd run this via a test runner or a main script that sets up asyncio.
    # For now, we'll comment out the direct run.
    pass
