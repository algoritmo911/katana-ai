from abc import ABC, abstractmethod
from typing import Optional, Any
import uuid

from katana.task_queue.models import Task, TaskStatus


class AbstractBroker(ABC):
    """
    Abstract base class for a task queue broker.
    """

    @abstractmethod
    async def enqueue(self, task: Task) -> None:
        pass

    @abstractmethod
    async def dequeue(self) -> Optional[Task]:
        pass

    @abstractmethod
    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        pass

    @abstractmethod
    async def update_task_status(self, task_id: uuid.UUID, status: "TaskStatus") -> bool:
        pass

    @abstractmethod
    async def mark_complete(self, task_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def complete_task(self, task_id: uuid.UUID, result: Any) -> bool:
        pass

    @abstractmethod
    async def mark_failed(self, task_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def task_exists(self, task_id: uuid.UUID) -> bool:
        pass


import asyncio
import heapq
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional


HeapItem = Tuple[int, datetime, datetime, uuid.UUID]


class InMemoryBroker(AbstractBroker):
    """
    In-memory implementation of the AbstractBroker.
    """

    def __init__(self):
        self._tasks: Dict[uuid.UUID, Task] = {}
        self._queue: List[HeapItem] = []
        self._lock = asyncio.Lock()

    async def enqueue(self, task: Task) -> None:
        async with self._lock:
            if task.id in self._tasks:
                print(
                    f"Warning: Task with ID {task.id} already exists. Skipping enqueue."
                )
                return

            task_to_store = task
            if task.status != TaskStatus.PENDING:
                task_to_store = task.with_status(TaskStatus.PENDING)

            self._tasks[task_to_store.id] = task_to_store
            heap_item: HeapItem = (
                task_to_store.priority,
                task_to_store.scheduled_at,
                task_to_store.created_at,
                task_to_store.id,
            )
            heapq.heappush(self._queue, heap_item)

    async def dequeue(self) -> Optional[Task]:
        async with self._lock:
            if not self._queue:
                return None

            priority, scheduled_at, created_at, task_id = self._queue[0]

            if scheduled_at > datetime.now(timezone.utc):
                return None

            heapq.heappop(self._queue)

            task = self._tasks.get(task_id)
            if not task:
                return None

            return task

    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task_status(self, task_id: uuid.UUID, status: TaskStatus) -> bool:
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                self._tasks[task_id] = task.with_status(status)
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
        return await self.update_task_status(task_id, TaskStatus.FAILED)

    async def task_exists(self, task_id: uuid.UUID) -> bool:
        async with self._lock:
            return task_id in self._tasks

    async def get_queue_size(self) -> int:
        async with self._lock:
            return len(self._queue)

    async def get_pending_task_count(self) -> int:
        async with self._lock:
            count = 0
            for _, _, _, task_id in self._queue:
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    count += 1
            return count
