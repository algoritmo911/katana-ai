from typing import Type, Dict, TypeVar
from loguru import logger

from src.katana.domain.commands import Command
# We are forward-declaring CommandHandler here. It will be created in the next step.
from src.katana.core.handlers import CommandHandler

T = TypeVar("T", bound=Command)

class CommandBus:
    """
    The CommandBus is the central dispatcher of the application.
    It maps command types to their respective handlers and executes them.
    This decouples the part of the code that issues the command (e.g., an adapter)
    from the part that executes the business logic (the handler).
    """

    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, command_cls: Type[T], handler: CommandHandler):
        """
        Registers a command handler for a specific command type.

        Args:
            command_cls: The class of the command (e.g., StartCommand).
            handler: An instance of the handler that will process the command.

        Raises:
            TypeError: If the provided classes are not of the expected type.
        """
        if not issubclass(command_cls, Command):
            raise TypeError("command_cls must be a subclass of Command")
        if not isinstance(handler, CommandHandler):
            raise TypeError("handler must be an instance of CommandHandler")

        logger.info(f"Registering handler '{handler.__class__.__name__}' for command '{command_cls.__name__}'.")
        self._handlers[command_cls] = handler

    async def dispatch(self, command: Command):
        """
        Dispatches a command to its registered handler.

        The bus finds the handler registered for the type of the given command
        and invokes its `handle` method.

        Args:
            command: An instance of a command to be dispatched.

        Returns:
            The result from the command handler's `handle` method.

        Raises:
            TypeError: If no handler is registered for the command type.
        """
        command_type = type(command)
        handler = self._handlers.get(command_type)

        if handler is None:
            logger.error(f"No handler registered for command: {command_type.__name__}")
            raise TypeError(f"No handler registered for {command_type.__name__}")

        logger.debug(f"Dispatching command '{command_type.__name__}' to handler '{handler.__class__.__name__}'.")

        # Add command details to the logging context for better observability.
        # Any log message within the `handle` method will have this extra info.
        with logger.contextualize(command_type=command_type.__name__, command_details=command.model_dump()):
            try:
                return await handler.handle(command)
            except Exception:
                logger.exception(
                    f"An exception occurred in handler '{handler.__class__.__name__}' "
                    f"while processing command '{command_type.__name__}'."
                )
                # Re-raise the exception so the caller (e.g., the adapter) can handle it,
                # for instance, by sending an error message to the user.
                raise
