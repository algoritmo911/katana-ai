from abc import ABC, abstractmethod
from loguru import logger

from src.katana.domain.commands import Command, StartCommand, PingCommand

class CommandHandler(ABC):
    """
    Abstract base class for all command handlers.

    Each handler is responsible for executing the business logic for a single
    type of command. Handlers should be stateless and rely on dependencies
    (like services) injected during their creation.
    """

    @abstractmethod
    async def handle(self, command: Command) -> str:
        """
        Executes the logic for the given command.

        Args:
            command: The command instance to be handled.

        Returns:
            A string result to be sent back to the user/caller.
        """
        raise NotImplementedError


class StartCommandHandler(CommandHandler):
    """
    Handler for the StartCommand.
    Welcomes a new user.
    """
    async def handle(self, command: StartCommand) -> str:
        """
        Handles the start command by generating a personalized welcome message.
        """
        logger.info(
            f"Handling StartCommand for user_id={command.user_id} "
            f"in chat_id={command.chat_id}."
        )
        return f"Welcome, {command.user_name}! This is Katana Bot, running on a new, modular core."


class PingCommandHandler(CommandHandler):
    """
    Handler for the PingCommand.
    Used for health checks.
    """
    async def handle(self, command: PingCommand) -> str:
        """
        Handles the ping command by returning a simple 'pong' response.
        This is a lightweight way to verify that the system is responsive.
        """
        logger.info(
            f"Handling PingCommand for user_id={command.user_id} "
            f"in chat_id={command.chat_id}."
        )
        return "pong"
