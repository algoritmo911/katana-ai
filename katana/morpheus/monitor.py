import time
import yaml
from typing import Dict, List, Set
from threading import Lock

class _ActivityMonitor:
    """
    A singleton class that monitors system-wide activity to determine if the
    system is idle. This is the core of the 'Circadian Rhythm'.
    """
    _instance = None
    _lock = Lock()

    def __init__(self):
        # This init should only be called once.
        print("Initializing Activity Monitor...")
        with open("katana/morpheus/morpheus_config.yml", "r") as f:
            config = yaml.safe_load(f)

        self.config = config['circadian_rhythm']
        self.thresholds = self.config['sleep_conditions']['thresholds']

        # In a real multi-threaded/multi-process app, these would need a more robust
        # implementation (e.g., using Redis or another shared memory store).
        self.request_timestamps: List[float] = []
        self.active_tasks: Set[str] = set()

    def log_request(self):
        """Logs an incoming API request."""
        with self._lock:
            self.request_timestamps.append(time.time())

    def register_task(self, task_id: str):
        """Registers the start of a background task."""
        with self._lock:
            self.active_tasks.add(task_id)

    def unregister_task(self, task_id: str):
        """Registers the end of a background task."""
        with self._lock:
            self.active_tasks.discard(task_id)

    def is_idle(self) -> bool:
        """
        Checks if all idleness conditions, based on the config, are met.
        """
        with self._lock:
            # 1. Check request count
            one_minute_ago = time.time() - 60
            # Filter out old timestamps to keep the list from growing indefinitely
            self.request_timestamps = [t for t in self.request_timestamps if t > one_minute_ago]
            if len(self.request_timestamps) > self.thresholds['max_requests_per_minute']:
                print(f"DEBUG: Activity detected: {len(self.request_timestamps)} recent requests.")
                return False

            # 2. Check active background tasks
            if len(self.active_tasks) > self.thresholds['max_active_background_tasks']:
                print(f"DEBUG: Activity detected: {len(self.active_tasks)} active tasks.")
                return False

            # 3. TODO: Add CPU check as per the TDD. This is a placeholder.
            # In a real scenario, this would use a library like `psutil`.
            # For now, we assume it passes if the other checks pass.

            # If all checks pass, the system is idle.
            return True

# The singleton instance. Other modules should import this instance.
activity_monitor = _ActivityMonitor()
