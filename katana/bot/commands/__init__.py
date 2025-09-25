# This file makes the `commands` directory a Python package.

# Import all modules in this directory to ensure commands are registered.
import pkgutil
import importlib

# The command_registry will be the single source of truth for all registered commands.
# It is initialized here to be accessible by all modules in this package.
command_registry = {}


def register_command(name):
    """
    A decorator to register a new command.
    The decorated function is expected to be an async function that takes
    (update: Update, context: ContextTypes.DEFAULT_TYPE) as arguments,
    which is the standard signature for a command handler in python-telegram-bot.
    """

    def decorator(func):
        # Store the command name and the handler function in the registry.
        if name in command_registry:
            # Optionally, you could raise an error or log a warning if a command is redefined.
            # For simplicity, we'll just overwrite it.
            pass
        command_registry[name] = func
        return func  # Return the original function

    return decorator


def load_commands():
    """
    Dynamically load all modules in the current package.
    This function is called to discover and register all commands
    defined in the various files of this directory.
    """
    # __path__ is a special attribute of packages, it's a list containing the name of the package's directory.
    # __name__ is the package's name.
    for _, module_name, _ in pkgutil.walk_packages(__path__, __name__ + "."):
        importlib.import_module(module_name)


# It's a common practice to offer a function that returns all the registered items.
def get_all_commands():
    """Returns a dictionary of all registered commands."""
    return command_registry