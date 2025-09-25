import logging
from telegram import Update
from telegram.ext import ContextTypes
from . import register_command

# Get a logger instance for this command module
logger = logging.getLogger(__name__)


@register_command("start")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    user_id = (
        update.effective_user.id if update.effective_user else "UnknownUser"
    )
    logger.debug(
        f"Entering start function for user_id: {user_id}",
        extra={"user_id": user_id},
    )
    logger.info(
        "Received /start command", extra={"user_id": user_id}
    )  # Removed unnecessary f-string
    await update.message.reply_text(
        "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
    )
    logger.debug(
        f"Exiting start function for user_id: {user_id}",
        extra={"user_id": user_id},
    )