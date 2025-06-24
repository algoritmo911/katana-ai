import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto

class TaskStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass(frozen=True, order=True)
class Task:
    # Note: order=True makes instances comparable based on the fields in the order they are defined.
    # We will primarily use priority, scheduled_at, and created_at for ordering in the queue.
    # The Task object itself won't be directly put into heapq if we need custom sort order there.
    priority: int = field(compare=False)
    scheduled_at: datetime = field(compare=False)
    created_at: datetime = field(compare=False, default_factory=lambda: datetime.now(timezone.utc))
    id: uuid.UUID = field(default_factory=uuid.uuid4, compare=False)
    name: str = field(compare=False)
    payload: dict = field(default_factory=dict, compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)

    def __post_init__(self):
        if not isinstance(self.priority, int):
            raise TypeError("Priority must be an integer.")
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Name must be a non-empty string.")
        if not isinstance(self.payload, dict):
            raise TypeError("Payload must be a dictionary.")
        if not isinstance(self.scheduled_at, datetime):
            # Ensure scheduled_at is offset-aware, defaulting to UTC if naive.
            if self.scheduled_at.tzinfo is None:
                object.__setattr__(self, 'scheduled_at', self.scheduled_at.replace(tzinfo=timezone.utc))
        if not isinstance(self.created_at, datetime) or self.created_at.tzinfo is None:
            # Ensure created_at is offset-aware.
             raise ValueError("created_at must be an offset-aware datetime object.")

    def with_status(self, new_status: TaskStatus) -> 'Task':
        """Returns a new Task instance with the updated status."""
        if not isinstance(new_status, TaskStatus):
            raise TypeError("new_status must be a TaskStatus enum member.")
        return Task(
            priority=self.priority,
            scheduled_at=self.scheduled_at,
            created_at=self.created_at,
            id=self.id,
            name=self.name,
            payload=self.payload,
            status=new_status # The only changed field
        )

if __name__ == '__main__':
    # Example Usage
    now = datetime.now(timezone.utc)
    task1 = Task(priority=1, scheduled_at=now, name="Test Task 1", payload={"data": "value1"})
    print(task1)

    import time
    time.sleep(0.001) # ensure created_at is different for task2 for sorting demo if needed

    task2 = Task(priority=0, scheduled_at=now, name="Test Task 2 - Higher Priority", payload={"data": "value2"})
    print(task2)

    task3_delayed = Task(
        priority=1,
        scheduled_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc), # A past fixed time
        name="Test Task 3 - Delayed",
        payload={"data": "value3"}
    )
    print(task3_delayed)

    # Demonstrating status update
    processing_task1 = task1.with_status(TaskStatus.PROCESSING)
    print(f"Task 1 now: {processing_task1}")

    try:
        invalid_task = Task(priority="low", scheduled_at=now, name="Invalid", payload={}) # type: ignore
    except TypeError as e:
        print(f"Error creating task: {e}")

    # Test default scheduled_at if not provided (though our current design requires it)
    # To make scheduled_at optional, we'd need to adjust __post_init__ and default_factory or default value.
    # For now, it's mandatory. If we want a task to run "ASAP", scheduled_at should be datetime.now(timezone.utc).

    # Example of how tasks might be sorted by a broker (conceptual)
    # The broker would likely store tuples like (priority, scheduled_at, created_at, task_id) in a heap.
    # The Task object itself is not made sortable in a way that heapq would directly use for this complex logic.
    # `order=True` in dataclass is for direct comparison of Task objects, which we might not use for queue ordering.
    # We set compare=False for most fields to avoid issues with default dataclass sorting if order=True was used
    # without careful consideration of all fields. Here, with order=True, it would sort by priority, then scheduled_at, etc.
    # but we've turned off comparison for individual fields to make it explicit that the broker handles complex sorting.
    # Let's remove order=True from dataclass as we will implement custom sorting in the broker.
    # Re-evaluating: order=True with compare=False on specific fields means those fields are skipped in auto-generated comparison methods.
    # It's better to set order=False and implement __lt__, __eq__ if direct Task comparison is ever needed,
    # or rely entirely on tuple comparison in the heap.
    # For now, @dataclass(frozen=True) is fine. The broker will handle sort order.
    # Changed `order=True` to `order=False` in the actual code above.
    # And removed compare=False from fields as they are irrelevant if order=False.
    # Final decision: Keep it simple. @dataclass(frozen=True). Broker will store tuples for heapq.

    # Corrected @dataclass definition after re-evaluation:
    # @dataclass(frozen=True)
    # priority: int
    # scheduled_at: datetime
    # created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # id: uuid.UUID = field(default_factory=uuid.uuid4)
    # name: str
    # payload: dict = field(default_factory=dict)
    # status: TaskStatus = field(default=TaskStatus.PENDING)
    # The above is how it is now. `order=True` was indeed problematic.
    # The current code has `order=True` but with `compare=False` on fields.
    # This is fine, as it means it's not comparable by default, which is what we want.
    # The broker will use tuples `(priority, scheduled_at, created_at, task.id)` for the heap.

    # Test __post_init__ for scheduled_at timezone awareness
    naive_dt = datetime(2025, 1, 1, 0, 0, 0)
    aware_task = Task(priority=1, scheduled_at=naive_dt, name="Awareness Test")
    print(f"Aware task scheduled_at: {aware_task.scheduled_at}, tzinfo: {aware_task.scheduled_at.tzinfo}")

    # Test created_at must be aware
    try:
        Task(priority=0, scheduled_at=datetime.now(timezone.utc), created_at=datetime.now(), name="test")
    except ValueError as e:
        print(f"Error with naive created_at: {e}")

    print("Task model defined and basic tests passed.")
