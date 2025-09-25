import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

import redis.asyncio as redis
from redis.asyncio.client import Pipeline

from katana.task_queue.broker import AbstractBroker
from katana.task_queue.models import Task, TaskStatus


class RedisBroker(AbstractBroker):
    """
    A Redis-based implementation of the task queue broker.
    This broker uses Redis to store and manage tasks, enabling communication
    between different processes or services.
    It uses several Redis keys, prefixed to avoid collisions:
    - A HASH to store task data: `katana:tasks`
    - A ZSET for scheduled tasks (score: timestamp): `katana:scheduled_queue`
    - A ZSET for due tasks (score: priority): `katana:due_queue`
    """

    def __init__(self, redis_url: str, prefix: str = "katana"):
        # The decode_responses=True is important to get strings back from Redis
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.tasks_key = f"{prefix}:tasks"
        self.due_queue_key = f"{prefix}:due_queue"
        self.scheduled_queue_key = f"{prefix}:scheduled_queue"

    def _serialize_task(self, task: Task) -> str:
        """Serializes a Task object to a JSON string."""
        # Special handling for pickled data
        if "task_data" in task.payload and isinstance(task.payload["task_data"], bytes):
            # dill output is bytes, which is not directly JSON serializable.
            # We will store it as a base64 encoded string.
            import base64
            payload = task.payload.copy()
            payload["task_data"] = base64.b64encode(payload["task_data"]).decode('ascii')
        else:
            payload = task.payload

        d = {
            "id": str(task.id),
            "name": task.name,
            "payload": payload,
            "priority": task.priority,
            "scheduled_at": task.scheduled_at.isoformat(),
            "created_at": task.created_at.isoformat(),
            "status": task.status.name,
            "result": task.result,
        }
        return json.dumps(d)

    def _deserialize_task(self, task_data: str) -> Task:
        """Deserializes a JSON string to a Task object."""
        d = json.loads(task_data)

        # Special handling for pickled data
        if "task_data" in d["payload"]:
            import base64
            d["payload"]["task_data"] = base64.b64decode(d["payload"]["task_data"])

        return Task(
            id=uuid.UUID(d["id"]),
            name=d["name"],
            payload=d["payload"],
            priority=d["priority"],
            scheduled_at=datetime.fromisoformat(d["scheduled_at"]),
            created_at=datetime.fromisoformat(d["created_at"]),
            status=TaskStatus[d["status"]],
            result=d.get("result"),
        )

    async def enqueue(self, task: Task) -> None:
        """Adds a task to the appropriate queue in Redis."""
        task_json = self._serialize_task(task)
        now_ts = datetime.now(timezone.utc).timestamp()
        scheduled_ts = task.scheduled_at.timestamp()

        async with self.redis.pipeline() as pipe:
            await pipe.hset(self.tasks_key, str(task.id), task_json)
            if scheduled_ts <= now_ts:
                await pipe.zadd(self.due_queue_key, {str(task.id): task.priority})
            else:
                await pipe.zadd(self.scheduled_queue_key, {str(task.id): scheduled_ts})
            await pipe.execute()

    async def _move_scheduled_tasks_to_due_queue(self) -> int:
        """
        Moves due tasks from scheduled to due queue.
        NOTE: This implementation is not atomic and can lead to race conditions
        under high concurrency from multiple workers. A Lua script would be
        required for true atomicity, but is not used to maintain compatibility
        with testing environments like the current version of `fakeredis`.
        """
        now_ts = datetime.now(timezone.utc).timestamp()
        # Find all task IDs that are due.
        due_task_ids = await self.redis.zrangebyscore(
            self.scheduled_queue_key, min="-inf", max=str(now_ts)
        )

        if not due_task_ids:
            return 0

        # For each due task, get its full data to find its priority.
        tasks_to_move = {}
        task_data_list = await self.redis.hmget(self.tasks_key, due_task_ids)

        for task_id, task_json in zip(due_task_ids, task_data_list):
            if task_json:
                task = self._deserialize_task(task_json)
                tasks_to_move[task_id] = task.priority

        if not tasks_to_move:
            return 0

        # Use a pipeline to move tasks atomically from Redis's perspective
        async with self.redis.pipeline() as pipe:
            # Add tasks to the due queue with their priority as score
            await pipe.zadd(self.due_queue_key, tasks_to_move)
            # Remove the moved tasks from the scheduled queue
            await pipe.zrem(self.scheduled_queue_key, *tasks_to_move.keys())
            await pipe.execute()

        return len(tasks_to_move)

    async def dequeue(self) -> Optional[Task]:
        """Dequeues the highest-priority task that is due."""
        await self._move_scheduled_tasks_to_due_queue()

        # Atomically get and remove the task with the lowest score (highest priority)
        # using ZPOPMIN.
        result = await self.redis.zpopmin(self.due_queue_key, 1)
        if not result:
            return None

        # result is like [('task_id_str', 0.0)]
        task_id, _ = result[0]
        return await self.get_task(uuid.UUID(task_id))

    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        """Retrieves a task by its ID from Redis."""
        task_json = await self.redis.hget(self.tasks_key, str(task_id))
        if not task_json:
            return None
        return self._deserialize_task(task_json)

    async def update_task_status(self, task_id: uuid.UUID, status: TaskStatus) -> bool:
        """Updates the status of a task in Redis."""
        # This is not atomic, but it's acceptable for status updates.
        task = await self.get_task(task_id)
        if not task:
            return False

        updated_task = task.with_status(status)
        task_json = self._serialize_task(updated_task)
        await self.redis.hset(self.tasks_key, str(task_id), task_json)
        return True

    async def mark_complete(self, task_id: uuid.UUID) -> bool:
        return await self.complete_task(task_id, result=None)

    async def complete_task(self, task_id: uuid.UUID, result: Any) -> bool:
        """Marks a task as COMPLETED in Redis and stores the result."""
        task = await self.get_task(task_id)
        if not task:
            return False

        updated_task = task.with_status(TaskStatus.COMPLETED).with_result(result)
        task_json = self._serialize_task(updated_task)
        await self.redis.hset(self.tasks_key, str(task_id), task_json)
        return True

    async def mark_failed(self, task_id: uuid.UUID) -> bool:
        return await self.update_task_status(task_id, TaskStatus.FAILED)

    async def task_exists(self, task_id: uuid.UUID) -> bool:
        """Checks if a task with the given ID exists in the broker."""
        return await self.redis.hexists(self.tasks_key, str(task_id))

    async def close(self):
        """Closes the Redis connection."""
        await self.redis.close()

    async def _clear_all_data_for_testing(self):
        """A helper method for tests to clean up Redis state."""
        await self.redis.delete(
            self.tasks_key, self.due_queue_key, self.scheduled_queue_key
        )
