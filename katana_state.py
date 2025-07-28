import queue
import uuid
from threading import Lock

class KatanaState:
    def __init__(self):
        self.command_queue = queue.Queue()
        self._lock = Lock()

    def enqueue(self, command_data):
        """Adds a command to the queue with a unique ID."""
        with self._lock:
            command_data['katana_uid'] = str(uuid.uuid4())
            self.command_queue.put(command_data)
            return command_data['katana_uid']

    def dequeue(self):
        """Removes and returns a command from the queue."""
        try:
            return self.command_queue.get_nowait()
        except queue.Empty:
            return None

    def task_done(self):
        """Indicates that a formerly enqueued task is complete."""
        self.command_queue.task_done()
