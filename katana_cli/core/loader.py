import pkgutil
import inspect
import importlib
from pathlib import Path
from katana_cli.commands.base import KatanaCommand

def load_commands():
    """
    Dynamically loads all commands from the 'katana_cli.commands' module.
    """
    commands = {}
    commands_dir = Path(__file__).parent.parent / "commands"
    for module_file in commands_dir.glob("*.py"):
        if module_file.name.startswith("_") or module_file.name == "base.py":
            continue

        module_name = f"katana_cli.commands.{module_file.stem}"
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, KatanaCommand) and obj is not KatanaCommand:
                commands[obj.name] = obj
    return commands
