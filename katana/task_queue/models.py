import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Optional, Any


class TaskStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass(frozen=True, order=True)
class Task:
    priority: int = field(compare=False)
    scheduled_at: datetime = field(compare=False)
    name: str = field(compare=False)

    payload: dict = field(default_factory=dict, compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    result: Optional[Any] = field(default=None, compare=False)
    created_at: datetime = field(
        compare=False, default_factory=lambda: datetime.now(timezone.utc)
    )
    id: uuid.UUID = field(default_factory=uuid.uuid4, compare=False)

    def __post_init__(self):
        if not isinstance(self.priority, int):
            raise TypeError("Priority must be an integer.")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Name must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise TypeError("Payload must be a dictionary.")
        if not isinstance(self.scheduled_at, datetime):
            if self.scheduled_at.tzinfo is None:
                object.__setattr__(
                    self, "scheduled_at", self.scheduled_at.replace(tzinfo=timezone.utc)
                )
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            raise ValueError("created_at must be an offset-aware datetime object.")

    def with_status(self, new_status: TaskStatus) -> "Task":
        if not isinstance(new_status, TaskStatus):
            raise TypeError("new_status must be a TaskStatus enum member.")
        return Task(
            priority=self.priority,
            scheduled_at=self.scheduled_at,
            name=self.name,
            payload=self.payload,
            status=new_status,
            result=self.result,
            created_at=self.created_at,
            id=self.id,
        )

    def with_result(self, result_data: Any) -> "Task":
        return Task(
            priority=self.priority,
            scheduled_at=self.scheduled_at,
            name=self.name,
            payload=self.payload,
            status=self.status,
            result=result_data,
            created_at=self.created_at,
            id=self.id,
        )


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    task1 = Task(
        priority=1, scheduled_at=now, name="Test Task 1", payload={"data": "value1"}
    )
    print(task1)

    import time

    time.sleep(0.001)

    task2 = Task(
        priority=0,
        scheduled_at=now,
        name="Test Task 2 - Higher Priority",
        payload={"data": "value2"},
    )
    print(task2)

    task3_delayed = Task(
        priority=1,
        scheduled_at=datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        ),
        name="Test Task 3 - Delayed",
        payload={"data": "value3"},
    )
    print(task3_delayed)

    processing_task1 = task1.with_status(TaskStatus.PROCESSING)
    print(f"Task 1 now: {processing_task1}")

    try:
        invalid_task = Task(priority="low", scheduled_at=now, name="Invalid", payload={})
    except TypeError as e:
        print(f"Error creating task: {e}")

    naive_dt = datetime(2025, 1, 1, 0, 0, 0)
    aware_task = Task(priority=1, scheduled_at=naive_dt, name="Awareness Test")
    print(
        f"Aware task scheduled_at: {aware_task.scheduled_at}, tzinfo: {aware_task.scheduled_at.tzinfo}"
    )

    try:
        Task(
            priority=0,
            scheduled_at=datetime.now(timezone.utc),
            created_at=datetime.now(),
            name="test",
        )
    except ValueError as e:
        print(f"Error with naive created_at: {e}")

    print("Task model defined and basic tests passed.")
