from typing import NamedTuple

class TaskResult(NamedTuple):
    """
    Represents the result of a single task execution.
    """
    success: bool
    details: str
    task_content: str
