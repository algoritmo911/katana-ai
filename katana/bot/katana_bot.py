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
logger = logging.getLogger("KatanaBotAI")


# --- Configuration & Log File Setup ---
# Token and keys from environment variables
TELEGRAM_TOKEN = os.environ.get("KATANA_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

BOT_LOG_DIR = Path(__file__).resolve().parent / "logs"
BOT_LOG_FILE = BOT_LOG_DIR / "katana_bot.log"

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
    user_name = update.effective_user.username if update.effective_user else "UnknownUsername"
    chat_id = update.effective_chat.id if update.effective_chat else "UnknownChat"
    logger.debug(
        "Entering start command handler.",
        extra={"user_id": user_id, "user_name": user_name, "chat_id": chat_id},
    )
    welcome_message = "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
    logger.info(
        "Received /start command.", extra={"user_id": user_id, "chat_id": chat_id}
    )
    await update.message.reply_text(welcome_message)
    logger.info(
        "Welcome message sent.",
        extra={"user_id": user_id, "chat_id": chat_id, "message_length": len(welcome_message)},
    )
    logger.debug(
        "Exiting start command handler.",
        extra={"user_id": user_id, "chat_id": chat_id},
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles non-command text messages by sending them to OpenAI GPT."""
    user_id = update.effective_user.id if update.effective_user else "UnknownUser"
    user_name = update.effective_user.username if update.effective_user else "UnknownUsername"
    chat_id = update.effective_chat.id if update.effective_chat else "UnknownChat"

    logger.debug(
        "Entering handle_message.",
        extra={"user_id": user_id, "user_name": user_name, "chat_id": chat_id},
    )

    if not update.message or not update.message.text:
        logger.warning(
            "Received message with no text content.",
            extra={"user_id": user_id, "chat_id": chat_id, "update_has_message": bool(update.message)},
        )
        # Optionally, send a message back to the user, or simply return.
        # await update.message.reply_text("I received an empty message. Please send some text.")
        logger.debug("Exiting handle_message: no text content.", extra={"user_id": user_id, "chat_id": chat_id})
        return

    user_text = update.message.text
    message_id = update.message.message_id

    logger.info(
        f"Received message (ID: {message_id}, Length: {len(user_text)}). Preview: '{user_text[:100]}'",
        extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "message_length": len(user_text)},
    )
    logger.debug(
        f"Full message text (ID: {message_id}): {user_text}",
        extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id},
    )

    if not client:
        logger.error(
            "OpenAI client not initialized. Cannot process message.",
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id},
        )
        await update.message.reply_text(
            "I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator."
        )
        logger.debug(
            "Exiting handle_message: OpenAI client not initialized.",
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id},
        )
        return

    try:
        model_used = "gpt-4"
        logger.debug(
            f"Preparing to send user text to OpenAI. Model: {model_used}.",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "model": model_used,
                "text_prefix": user_text[:50],
            },
        )
        logger.info(
            f"Sending to OpenAI (model: {model_used}). User text preview: '{user_text[:50]}...'",
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "model": model_used},
        )

        completion = client.chat.completions.create(
            model=model_used, messages=[{"role": "user", "content": user_text}]
        )
        logger.debug(
            "Received response from OpenAI API.",
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "openai_response_id": completion.id if completion else "N/A"},
        )

        ai_reply = completion.choices[0].message.content.strip()
        logger.info(
            f"OpenAI reply received (Length: {len(ai_reply)}). Preview: '{ai_reply[:50]}...'",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_length": len(ai_reply),
                "openai_finish_reason": completion.choices[0].finish_reason if completion and completion.choices else "N/A",
            },
        )
        logger.debug(
            f"Full OpenAI reply: {ai_reply}",
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id},
        )

        await update.message.reply_text(ai_reply)
        logger.info(
            "Successfully sent AI reply to user.",
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id},
        )

    except AuthenticationError as e:
        logger.error(
            f"OpenAI Authentication Error: {e}. Ensure the API key is correctly configured and valid.",
            exc_info=True, # Adding exc_info for full traceback in logs
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "error_type": type(e).__name__},
        )
        await update.message.reply_text(
            "Error: OpenAI authentication failed. Please check the API key configuration with the administrator."
        )
    except RateLimitError as e:
        logger.error(
            f"OpenAI Rate Limit Error: {e}. The bot may be sending requests too frequently or has exceeded its quota.",
            exc_info=True,
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "error_type": type(e).__name__},
        )
        await update.message.reply_text(
            "Error: OpenAI rate limit exceeded. Please try again later."
        )
    except APIError as e:  # More general API errors from OpenAI v1.x
        logger.error(
            f"OpenAI API Error: {e}. This could be due to various issues with the OpenAI service or the request.",
            exc_info=True,
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "error_type": type(e).__name__},
        )
        await update.message.reply_text(
            f"An error occurred with the OpenAI API: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in handle_message: {e}",
            exc_info=True, # Ensure traceback is always logged for unexpected errors
            extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "error_type": type(e).__name__},
        )
        await update.message.reply_text(
            "Sorry, an unexpected error occurred while processing your message."
        )

    logger.debug(
        "Exiting handle_message.",
        extra={"user_id": user_id, "chat_id": chat_id, "message_id": message_id if 'message_id' in locals() else "N/A"},
    )


# --- Main Bot Setup ---
def main():
    """Starts the bot."""
    global logger  # Ensure we are modifying the global logger instance
    logger = setup_logger(
        "KatanaBotAI", str(BOT_LOG_FILE), level=logging.DEBUG
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
