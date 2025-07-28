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
        self.timestamp = datetime.utcnow()
        self.parent_id = parent_id
        self.children_ids = []

    def add_child(self, child_id):
        """Adds a child command's ID to this command's list of children."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def __repr__(self):
        return f"Command(id={self.id}, type='{self.type}', parent='{self.parent_id}')"


class CommandGraph:
    """Manages the collection of all commands and their relationships."""

    def __init__(self):
        self._commands = {}  # Store commands by their ID

    def add_command(self, command):
        """Adds a command to the graph and links it to its parent."""
        if command.id in self._commands:
            # Handle potential ID collision if necessary
            return
        self._commands[command.id] = command
        if command.parent_id and command.parent_id in self._commands:
            parent_command = self._commands[command.parent_id]
            parent_command.add_child(command.id)

    def get_command(self, command_id):
        """Retrieves a command by its ID."""
        return self._commands.get(command_id)

    def to_dot(self):
        """Generates a DOT language representation of the command graph."""
        dot_lines = ["digraph CommandGraph {"]
        dot_lines.append('  rankdir="TB";')
        dot_lines.append('  node [shape=box, style="rounded,filled", fillcolor="lightblue"];')
        dot_lines.append('  edge [arrowhead="vee"];')


        for cmd_id, command in self._commands.items():
            label = f"ID: {command.id}\\nType: {command.type}\\nModule: {command.module}"
            dot_lines.append(f'  "{cmd_id}" [label="{label}"];')

        for cmd_id, command in self._commands.items():
            if command.parent_id and command.parent_id in self._commands:
                dot_lines.append(f'  "{command.parent_id}" -> "{cmd_id}";')

        dot_lines.append("}")
        return "\n".join(dot_lines)
