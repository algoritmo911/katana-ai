import logging
from telegram import Update
from telegram.ext import ContextTypes
from . import register_command, get_all_commands

# Get a logger instance for this command module
logger = logging.getLogger(__name__)


@register_command("help")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays a list of available commands."""
    user_id = (
        update.effective_user.id if update.effective_user else "UnknownUser"
    )
    logger.debug(
        f"Entering help_command for user_id: {user_id}",
        extra={"user_id": user_id},
    )
    logger.info("Received /help command", extra={"user_id": user_id})

    # Get all registered commands from the registry
    all_commands = get_all_commands()

    # Create a formatted string with the list of commands
    # The `all_commands` dictionary keys are the command names
    if all_commands:
        # We add a '/' prefix to each command name for the help message
        help_text = "Available commands:\n" + "\n".join(
            f"/{command}" for command in sorted(all_commands.keys())
        )
    else:
        help_text = "No commands are currently available."

    await update.message.reply_text(help_text)
    logger.debug(
        f"Exiting help_command for user_id: {user_id}",
        extra={"user_id": user_id},
    )