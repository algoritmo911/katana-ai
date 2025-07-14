import json
import os
from datetime import datetime
from typing import Dict, List, Any

class Memory:
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = memory_dir
        self.dreams_dir = os.path.join(memory_dir, "dreams")
        self.tasks_dir = os.path.join(memory_dir, "tasks")
        os.makedirs(self.dreams_dir, exist_ok=True)
        os.makedirs(self.tasks_dir, exist_ok=True)

    def _save_memory(self, memory_type: str, memory_data: Dict[str, Any]):
        """Saves a memory to the appropriate directory."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        memory_dir = os.path.join(self.memory_dir, memory_type, date_str)
        os.makedirs(memory_dir, exist_ok=True)
        file_path = os.path.join(memory_dir, f"{time_str}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=4)

    def add_dream(self, dream_text: str):
        """Adds a dream to the memory."""
        memory_data = {
            "type": "dream",
            "timestamp": datetime.now().isoformat(),
            "content": dream_text,
        }
        self._save_memory("dreams", memory_data)

    def add_task(self, task_text: str):
        """Adds a task to the memory."""
        memory_data = {
            "type": "task",
            "timestamp": datetime.now().isoformat(),
            "content": task_text,
        }
        self._save_memory("tasks", memory_data)
