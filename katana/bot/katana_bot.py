import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI, APIError, AuthenticationError, RateLimitError # For openai >= 1.0.0
import traceback # For more detailed error logging

# --- Configuration ---
# Token and keys from environment variables
TELEGRAM_TOKEN = os.environ.get("KATANA_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- Initialize OpenAI Client (v1.x.x) ---
client: OpenAI = None # type: ignore
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
    print(f"[KatanaBotAI] OpenAI client initialized with API key ending: ...{OPENAI_API_KEY[-4:] if len(OPENAI_API_KEY) > 4 else 'KEY_TOO_SHORT'}.")
else:
    print(f"[KatanaBotAI] WARNING: OPENAI_API_KEY not found, OpenAI client not initialized. OpenAI features will be disabled.")

# Local print logger for the bot (defined early for use by startup messages if needed)
def log_local_bot_event(level, message): # Added level for consistency, though not used in original
    from datetime import datetime # Keep import local if function is moved around
    print(f"[KatanaBotAI:{level.upper()}] {datetime.utcnow().isoformat()} - {message}")


# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    user_id = update.effective_user.id if update.effective_user else 'UnknownUser'
    log_local_bot_event("info", f"Received /start command from user {user_id}")
    await update.message.reply_text("⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles non-command text messages by sending them to OpenAI GPT."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_id = update.effective_user.id if update.effective_user else 'UnknownUser'
    log_local_bot_event("info", f"Received message from user {user_id}: {user_text[:100]}") # Log truncated message

    if not client: # Check if OpenAI client is initialized
        log_local_bot_event("error", "OpenAI client not initialized. Cannot process message.")
        await update.message.reply_text("I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator.")
        return

    try:
        log_local_bot_event("info", f"Sending to OpenAI (GPT-4 model, user: {user_id}): {user_text[:50]}...")
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_text}]
        )
        ai_reply = completion.choices[0].message.content.strip()
        log_local_bot_event("info", f"OpenAI reply for user {user_id}: {ai_reply[:50]}...")
        await update.message.reply_text(ai_reply)

    except AuthenticationError as e:
        log_local_bot_event("error", f"OpenAI Authentication Error: {e}. Check your API key.")
        await update.message.reply_text("Error: OpenAI authentication failed. Please check the API key configuration with the administrator.")
    except RateLimitError as e:
        log_local_bot_event("error", f"OpenAI Rate Limit Error: {e}.")
        await update.message.reply_text("Error: OpenAI rate limit exceeded. Please try again later.")
    except APIError as e: # More general API errors from OpenAI v1.x
        log_local_bot_event("error", f"OpenAI API Error: {e}")
        await update.message.reply_text(f"An error occurred with the OpenAI API: {str(e)}")
    except Exception as e:
        log_local_bot_event("critical_error", f"An unexpected error occurred in handle_message: {e}")
        log_local_bot_event("critical_error", traceback.format_exc())
        await update.message.reply_text("Sorry, an unexpected error occurred while processing your message.")

# --- Main Bot Setup ---
def main():
    """Starts the bot."""
    if not TELEGRAM_TOKEN:
        log_local_bot_event("critical_error", "Telegram bot cannot start: KATANA_TELEGRAM_TOKEN environment variable not set.")
        return
    if not OPENAI_API_KEY: # Already checked, but good for main entry point
        log_local_bot_event("critical_error", "OpenAI API Key not set. Message handling will fail.")
        # Allow bot to start for /start command, but message handling will fail gracefully.

    log_local_bot_event("info", f"Initializing Katana Telegram Bot (AI Chat Mode) with token ending: ...{TELEGRAM_TOKEN[-4:] if len(TELEGRAM_TOKEN) > 4 else 'TOKEN_TOO_SHORT'}")

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log_local_bot_event("info", "Katana Telegram Bot (AI Chat Mode) is running. Press Ctrl-C to stop.")
    try:
        application.run_polling()
    except Exception as e_poll:
        log_local_bot_event("critical_error", f"Error during bot polling: {e_poll}")
        log_local_bot_event("critical_error", traceback.format_exc())
    finally:
        log_local_bot_event("info", "Katana Telegram Bot (AI Chat Mode) stopped.")

if __name__ == '__main__':
    # To run this:
    # 1. pip install python-telegram-bot "openai>=1.0.0"
    # 2. Set KATANA_TELEGRAM_TOKEN environment variable.
    # 3. Set OPENAI_API_KEY environment variable.
    # 4. Run: python katana_bot.py
    main()
