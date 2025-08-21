from typing import NamedTuple

class TaskResult(NamedTuple):
    success: bool
    details: str
    task_content: str
