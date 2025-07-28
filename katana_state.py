import queue
import uuid
from threading import Lock

class KatanaState:
    def __init__(self):
        self.command_queue = queue.PriorityQueue()
        self.cancelled_commands = set()
        self.command_counter = 0
        self._lock = Lock()

    def enqueue(self, command_data):
        """Adds a command to the queue with a unique ID."""
        with self._lock:
            command_data['katana_uid'] = str(uuid.uuid4())
            priority = command_data.get("priority", 100)
            self.command_queue.put((priority, self.command_counter, command_data))
            self.command_counter += 1
            return command_data['katana_uid']

    def dequeue(self):
        """Removes and returns a command from the queue."""
        try:
            _, _, command_data = self.command_queue.get_nowait()
            return command_data
        except queue.Empty:
            return None

    def task_done(self):
        """Indicates that a formerly enqueued task is complete."""
        self.command_queue.task_done()

    def cancel_command(self, command_id):
        """Marks a command as cancelled."""
        with self._lock:
            self.cancelled_commands.add(command_id)
