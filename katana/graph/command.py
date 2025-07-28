import uuid
from datetime import datetime

class Command:
    """Represents a command and its position in the command graph."""

    def __init__(self, command_data, parent_id=None):
        """
        Initializes a Command object.

        Args:
            command_data (dict): The raw command data from the message.
            parent_id (str, optional): The ID of the parent command. Defaults to None.
        """
        self.id = command_data.get('id', str(uuid.uuid4()))
        self.type = command_data.get('type')
        self.module = command_data.get('module')
        self.args = command_data.get('args', {})
        self.started_at = datetime.now()
        self.finished_at = None
        self.status = "RUNNING"
        self.parent_id = parent_id
        self.children_ids = []

    def add_child(self, child_id):
        """Adds a child command's ID to this command's list of children."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def to_dict(self):
        """Returns a dictionary representation of the command."""
        return {
            "id": self.id,
            "type": self.type,
            "module": self.module,
            "args": self.args,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
        }

    @classmethod
    def from_dict(cls, data):
        """Creates a Command object from a dictionary."""
        command = cls(data)
        command.started_at = datetime.fromisoformat(data["started_at"])
        if data["finished_at"]:
            command.finished_at = datetime.fromisoformat(data["finished_at"])
        command.status = data["status"]
        command.parent_id = data["parent_id"]
        command.children_ids = data["children_ids"]
        return command

    def __repr__(self):
        return f"Command(id={self.id}, type='{self.type}', parent='{self.parent_id}')"
