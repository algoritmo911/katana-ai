import pkgutil
import inspect
import importlib
from pathlib import Path
from katana_cli.commands.base import KatanaCommand

def load_commands():
    """
    Dynamically loads all commands from the 'katana_cli.commands' module.
    """
    print("Loading commands...")
    commands = {}
    commands_dir = Path(__file__).parent.parent / "commands"
    print(f"Commands dir: {commands_dir}")
    for module_file in commands_dir.glob("*.py"):
        print(f"Found module: {module_file}")
        if module_file.name.startswith("_") or module_file.name == "base.py":
            continue

        module_name = f"katana_cli.commands.{module_file.stem}"
        print(f"Importing module: {module_name}")
        module = importlib.import_module(module_name)
        if module_name == "katana_cli.commands.cancel":
            print(f"Members of cancel module: {inspect.getmembers(module)}")
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, KatanaCommand) and obj is not KatanaCommand:
                print(f"Found command: {obj.name}")
                commands[obj.name] = obj
    print(f"Loaded commands: {commands.keys()}")
    return commands
