import json
from rich.tree import Tree
from rich import print as rprint
from .command import Command

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

    def get_roots(self):
        """Returns a list of root commands (commands with no parent)."""
        return [cmd for cmd in self._commands.values() if cmd.parent_id is None]

    def get_by_status(self, status):
        """Returns a list of commands with the given status."""
        return [cmd for cmd in self._commands.values() if cmd.status == status]

    def save_to_file(self, path):
        """Saves the command graph to a JSON file."""
        with open(path, "w") as f:
            json.dump([cmd.to_dict() for cmd in self._commands.values()], f, indent=2)

    def load_from_file(self, path):
        """Loads the command graph from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
            self._commands = {cmd_data["id"]: Command.from_dict(cmd_data) for cmd_data in data}

    def visualize(self):
        """Visualizes the command graph using rich.tree."""
        roots = self.get_roots()
        if not roots:
            rprint("No commands in the graph.")
            return

        for root in roots:
            tree = Tree(f"**{root.type}** ({root.id}) - {root.status}")
            self._build_tree(tree, root)
            rprint(tree)

    def _build_tree(self, tree, command):
        """Recursively builds the rich.tree."""
        for child_id in command.children_ids:
            child = self.get_command(child_id)
            if child:
                child_tree = tree.add(f"**{child.type}** ({child.id}) - {child.status}")
                self._build_tree(child_tree, child)

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
