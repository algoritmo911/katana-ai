import os
import logging

# Removed: from logging.handlers import RotatingFileHandler
# Removed: import json
# Removed: from datetime import datetime, timezone
from pathlib import Path
from katana.utils.logging_config import (
    setup_logger,
)  # Import the new setup function
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import (
    OpenAI,
    APIError,
    AuthenticationError,
    RateLimitError,
)  # For openai >= 1.0.0
import traceback


# --- Initialize Logger ---
# The actual logger object is now configured and retrieved via setup_logger.
# We still define a global 'logger' variable for the rest of the script to use.
# The setup_logger call will be made in main().
logger = logging.getLogger("KatanaBotAI") # Default logger instance

# --- Configuration & Log File Setup ---
# Token and keys from environment variables
TELEGRAM_TOKEN = os.environ.get("KATANA_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Determine if running in development mode (e.g., via environment variable)
# This will be passed to setup_logger.
IS_DEV_MODE = os.environ.get("ENV_MODE", "").lower() == "dev"

# Log file will be command_telemetry.log as per new requirements for the telemetry logger
LOG_FILE_NAME = "command_telemetry.log"
BOT_LOG_DIR = Path(__file__).resolve().parent / "logs" # Retain logs subdirectory for organization
BOT_LOG_FILE = BOT_LOG_DIR / LOG_FILE_NAME # Path object for the log file

# --- Initialize OpenAI Client (v1.x.x) ---
client: OpenAI = None  # type: ignore
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Logger will be configured in main() before this is needed for file logging
else:
    # Logger will be configured in main()
    pass


# --- Bot Command Handlers ---
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles non-command text messages by sending them to OpenAI GPT."""
    user_id = (
        update.effective_user.id if update.effective_user else "UnknownUser"
    )  # Moved up for earlier logging
    logger.debug(
        f"Entering handle_message for user_id: {user_id}",
        extra={"user_id": user_id},
    )
    if not update.message or not update.message.text:
        logger.debug(
            "Empty message received, exiting.", extra={"user_id": user_id}
        )
        return

    user_text = update.message.text
    logger.info(
        f"Received message: {user_text[:100]}", extra={"user_id": user_id}
    )  # Log truncated message
    logger.debug(f"Full message text: {user_text}", extra={"user_id": user_id})

    if not client:  # Check if OpenAI client is initialized
        logger.error(
            "OpenAI client not initialized. Cannot process message.",
            extra={"user_id": user_id},
        )
        await update.message.reply_text(
            "I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator."
        )
        logger.debug(
            "Exiting handle_message due to uninitialized OpenAI client.",
            extra={"user_id": user_id},
        )
        return

    try:
        logger.debug(
            f"Attempting to send to OpenAI. Model: gpt-4.",
            extra={"user_id": user_id, "text_prefix": user_text[:50]},
        )
        logger.info(
            f"Sending to OpenAI (GPT-4 model): {user_text[:50]}...",
            extra={"user_id": user_id},
        )
        completion = client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": user_text}]
        )
        ai_reply = completion.choices[0].message.content.strip()
        logger.info(
            f"OpenAI reply: {ai_reply[:50]}...", extra={"user_id": user_id}
        )
        logger.debug(
            f"Full OpenAI reply: {ai_reply}", extra={"user_id": user_id}
        )
        await update.message.reply_text(ai_reply)

    except AuthenticationError as e:
        logger.error(
            f"OpenAI Authentication Error: {e}. Check your API key.",
            extra={"user_id": user_id},
        )
        await update.message.reply_text(
            "Error: OpenAI authentication failed. Please check the API key configuration with the administrator."
        )
    except RateLimitError as e:
        logger.error(
            f"OpenAI Rate Limit Error: {e}.", extra={"user_id": user_id}
        )
        await update.message.reply_text(
            "Error: OpenAI rate limit exceeded. Please try again later."
        )
    except APIError as e:  # More general API errors from OpenAI v1.x
        logger.error(f"OpenAI API Error: {e}", extra={"user_id": user_id})
        await update.message.reply_text(
            f"An error occurred with the OpenAI API: {str(e)}"  # noqa: F541, f-string is used
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in handle_message: {e}",  # noqa: F541, f-string is used
            extra={"user_id": user_id, "traceback": traceback.format_exc()},
        )
        await update.message.reply_text(
            "Sorry, an unexpected error occurred while processing your message."
        )
    logger.debug(
        f"Exiting handle_message for user_id: {user_id}",
        extra={"user_id": user_id},
    )


# --- Main Bot Setup ---
def main():
    """Starts the bot."""
    global logger  # Ensure we are modifying the global logger instance
    # Update the setup_logger call to include dev_mode and use the new log file name.
    # The BOT_LOG_FILE path object now correctly points to "command_telemetry.log" within the "logs" dir.
    logger = setup_logger(
        logger_name="KatanaBotAI",
        log_file_path_str=str(BOT_LOG_FILE),
        level=logging.DEBUG,
        dev_mode=IS_DEV_MODE,  # Pass the dev_mode status
    )

    # --- Initial Status Logging (after logger is fully configured) ---
    # Note: BOT_LOG_DIR creation is handled by setup_logger
    if OPENAI_API_KEY:
        logger.info(
            f"OpenAI client initialized with API key ending: ...{OPENAI_API_KEY[-4:] if len(OPENAI_API_KEY) > 4 else 'KEY_TOO_SHORT'}."
        )
    else:
        logger.warning(
            "OPENAI_API_KEY not found, OpenAI client not initialized. OpenAI features will be disabled."
        )

    if not TELEGRAM_TOKEN:
        logger.critical(
            "Telegram bot cannot start: KATANA_TELEGRAM_TOKEN environment variable not set."
        )
        return
    if not OPENAI_API_KEY:  # Already checked, but good for main entry point
        logger.critical("OpenAI API Key not set. Message handling will fail.")
        # Allow bot to start for /start command, but message handling will fail gracefully.

    logger.info(
        f"Initializing Katana Telegram Bot (AI Chat Mode) with token ending: ...{TELEGRAM_TOKEN[-4:] if len(TELEGRAM_TOKEN) > 4 else 'TOKEN_TOO_SHORT'}"
    )

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info(
        "Katana Telegram Bot (AI Chat Mode) is running. Press Ctrl-C to stop."
    )
    try:
        # --- Sample logs for review ---
        logger.debug(
            "This is a sample debug message for bot review.",
            extra={
                "user_id": "test_review_user_123",
                "detail": "bot_debug_info",
            },
        )
        logger.info(
            "This is a sample info message for bot review.",
            extra={"user_id": "test_review_user_123"},
        )
        logger.warning(
            "This is a sample bot warning message.",
            extra={
                "user_id": "test_review_user_123",
                "warning_type": "config_issue",
            },
        )
        logger.error(
            "This is a sample bot error message, no exc_info.",
            extra={
                "user_id": "test_review_user_123",
                "error_event": "mock_event_failure",
            },
        )
        try:
            data = {}
            _ = data["missing_key"]  # Accessing missing key to cause KeyError
        except KeyError as e:
            logger.error(
                "Sample bot error with simulated KeyError.",
                exc_info=True,
                extra={
                    "user_id": "test_review_user_123",
                    "attempted_action": "dict_access",
                    "key_error": str(e),
                },
            )
            logger.critical(
                "Sample bot critical message after simulated KeyError.",
                extra={
                    "user_id": "test_review_user_123",
                    "next_step": "data_integrity_check",
                },
            )
        # --- End of sample logs for review ---

        # Only run polling if we intend to start the bot fully for this test run.
        # For sample log generation, we might not need this if it exits due to missing tokens.
        # However, if tokens ARE set, this will run.
        # For this review, assume we want it to try to run normally after logging samples.
        application.run_polling()

    except Exception as e_poll:
        logger.critical(
            f"Error during bot polling: {e_poll}",
            extra={"traceback": traceback.format_exc()},
        )
    finally:
        logger.info(
            "Katana Telegram Bot (AI Chat Mode) stopped."
        )  # This will be logged on normal exit too.


if __name__ == "__main__":
    # To run this:
    # 1. pip install python-telegram-bot "openai>=1.0.0"
    # 2. Set KATANA_TELEGRAM_TOKEN environment variable.
    # 3. Set OPENAI_API_KEY environment variable.
    # 4. Run: python katana_bot.py
    main()
