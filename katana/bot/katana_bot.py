import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI, APIError, AuthenticationError, RateLimitError # For openai >= 1.0.0
import traceback # For more detailed error logging
import logging # Import logging for setup_logging level
from katana.logger import setup_logging, get_logger
from katana.utils.telemetry import trace_command # Import the decorator

# --- Initialize Logging ---
setup_logging(log_level=logging.INFO) # Or logging.DEBUG, etc.
logger = get_logger(__name__) # Get a logger for this module

# --- Configuration ---
# Token and keys from environment variables
TELEGRAM_TOKEN = os.environ.get("KATANA_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- Initialize OpenAI Client (v1.x.x) ---
client: OpenAI = None # type: ignore
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
    logger.info(
        f"OpenAI client initialized with API key ending: ...{OPENAI_API_KEY[-4:] if len(OPENAI_API_KEY) > 4 else 'KEY_TOO_SHORT'}.",
        extra={'user_id': 'system', 'chat_id': 'system', 'message_id': 'init'}
    )
else:
    logger.warning(
        "OPENAI_API_KEY not found, OpenAI client not initialized. OpenAI features will be disabled.",
        extra={'user_id': 'system', 'chat_id': 'system', 'message_id': 'init_warn'}
    )

# --- Bot Command Handlers ---
# The @trace_command decorator expects user_id and context_id to be passed as kwargs
# to the decorated function. So we define helper functions that will be decorated.

async def _start_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, context_id: str):
    """Core logic for the /start command."""
    message_id_str = str(update.message.message_id) if update.message else 'UnknownMessage_start'
    log_context_start = {'user_id': user_id, 'chat_id': context_id, 'message_id': message_id_str}
    logger.info(f"Executing /start command logic for user {user_id}", extra=log_context_start)

    reply_text = "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
    await update.message.reply_text(reply_text)
    return reply_text # Return the reply for tracing

async def _handle_message_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, context_id: str):
    """Core logic for handling text messages."""
    if not update.message or not update.message.text:
        return "No message text found."

    user_text = update.message.text
    message_id_str = str(update.message.message_id) if update.message else 'UnknownMessage_handle'
    log_context_msg = {'user_id': user_id, 'chat_id': context_id, 'message_id': message_id_str}

    logger.info(f"Executing message handling logic for user {user_id}: {user_text[:100]}", extra=log_context_msg)

    if not client:
        logger.error("OpenAI client not initialized. Cannot process message.", extra=log_context_msg)
        reply_text = "I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator."
        await update.message.reply_text(reply_text)
        return reply_text

    try:
        logger.info(f"Sending to OpenAI (GPT-4 model, user: {user_id}): {user_text[:50]}...", extra=log_context_msg)
        completion = client.chat.completions.create(
            model="gpt-4", # Consider making model configurable
            messages=[{"role": "user", "content": user_text}]
        )
        ai_reply = completion.choices[0].message.content.strip()
        logger.info(f"OpenAI reply for user {user_id}: {ai_reply[:50]}...", extra=log_context_msg)
        await update.message.reply_text(ai_reply)
        return ai_reply # Return AI reply for tracing

    except AuthenticationError as e:
        logger.error(f"OpenAI Authentication Error: {e}. Check your API key.", extra=log_context_msg)
        reply_text = "Error: OpenAI authentication failed. Please check the API key configuration with the administrator."
        await update.message.reply_text(reply_text)
        raise # Re-raise to be caught by decorator's exception handling
    except RateLimitError as e:
        logger.error(f"OpenAI Rate Limit Error: {e}.", extra=log_context_msg)
        reply_text = "Error: OpenAI rate limit exceeded. Please try again later."
        await update.message.reply_text(reply_text)
        raise
    except APIError as e:
        logger.error(f"OpenAI API Error: {e}", extra=log_context_msg)
        reply_text = f"An error occurred with the OpenAI API: {str(e)}"
        await update.message.reply_text(reply_text)
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred in _handle_message_logic: {e}", extra=log_context_msg)
        logger.critical(traceback.format_exc(), extra=log_context_msg)
        reply_text = "Sorry, an unexpected error occurred while processing your message."
        await update.message.reply_text(reply_text)
        raise


# Decorated versions of the handler logic
@trace_command
async def traced_start_command_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, context_id: str):
    return await _start_command_logic(update, context, user_id=user_id, context_id=context_id)

@trace_command
async def traced_handle_message_logic(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, context_id: str):
    # The first two arguments (update, context) will go into *args for the decorator,
    # user_id and context_id will go into **kwargs for the decorator.
    return await _handle_message_logic(update, context, user_id=user_id, context_id=context_id)


# Actual handlers called by telegram.ext framework
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    user_id_str = str(update.effective_user.id) if update.effective_user else 'UnknownUser'
    chat_id_str = str(update.effective_chat.id) if update.effective_chat else 'UnknownChat'
    # Call the traced logic, passing user_id and context_id as kwargs
    await traced_start_command_logic(update, context, user_id=user_id_str, context_id=chat_id_str)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles non-command text messages by sending them to OpenAI GPT."""
    user_id_str = str(update.effective_user.id) if update.effective_user else 'UnknownUser'
    chat_id_str = str(update.effective_chat.id) if update.effective_chat else 'UnknownChat'
    # Call the traced logic, passing user_id and context_id as kwargs
    await traced_handle_message_logic(update, context, user_id=user_id_str, context_id=chat_id_str)


# --- Main Bot Setup ---
def main():
    """Starts the bot."""
    system_context = {'user_id': 'system', 'chat_id': 'system'}

    if not TELEGRAM_TOKEN:
        logger.critical(
            "Telegram bot cannot start: KATANA_TELEGRAM_TOKEN environment variable not set.",
            extra={**system_context, 'message_id': 'init_main_token_fail'}
        )
        return
    if not OPENAI_API_KEY:
        logger.warning( # Changed to warning as bot can start but features will be limited
            "OPENAI_API_KEY not set. OpenAI features will be disabled.",
            extra={**system_context, 'message_id': 'init_main_openai_warn'}
        )

    logger.info(
        f"Initializing Katana Telegram Bot (AI Chat Mode) with token ending: ...{TELEGRAM_TOKEN[-4:] if len(TELEGRAM_TOKEN) > 4 else 'TOKEN_TOO_SHORT'}",
        extra={**system_context, 'message_id': 'init_main_start'}
    )

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start)) # Uses the wrapper 'start'
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)) # Uses the wrapper 'handle_message'

    logger.info(
        "Katana Telegram Bot (AI Chat Mode) is running. Press Ctrl-C to stop.",
        extra={**system_context, 'message_id': 'init_main_running'}
    )
    logger.info("Bot started.", extra={**system_context, 'message_id': 'bot_startup_event'})

    try:
        application.run_polling()
    except Exception as e_poll:
        logger.critical(
            f"Error during bot polling: {e_poll}",
            extra={**system_context, 'message_id': 'main_poll_error'}
        )
        logger.critical(
            traceback.format_exc(),
            extra={**system_context, 'message_id': 'main_poll_traceback'}
        )
    finally:
        logger.info(
            "Katana Telegram Bot (AI Chat Mode) stopping...",
            extra={**system_context, 'message_id': 'bot_stopping_event'}
        )
        logger.info(
            "Katana Telegram Bot (AI Chat Mode) stopped.",
            extra={**system_context, 'message_id': 'init_main_stopped'}
        )


if __name__ == '__main__':
    # To run this:
    # 1. pip install python-telegram-bot "openai>=1.0.0"
    # 2. Set KATANA_TELEGRAM_TOKEN environment variable.
    # 3. Set OPENAI_API_KEY environment variable.
    # 4. Run: python katana_bot.py
    main()
