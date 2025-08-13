import os
import traceback
from pathlib import Path

from katana.utils.telemetry_provider import (
    setup_telemetry,
    get_logger,
    get_tracer,
    log_event,
    log_unstructured_message,
)
from opentelemetry import trace
from opentelemetry.logs import SeverityNumber
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
)

# --- Global Variables ---
# The logger will be initialized in main() after telemetry is set up.
logger = None

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("KATANA_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- Initialize OpenAI Client ---
client: OpenAI = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    user_id = update.effective_user.id if update.effective_user else "UnknownUser"

    log_event(
        logger,
        "bot.command.start.received",
        body={"user_id": str(user_id), "message": "Received /start command"},
        severity=SeverityNumber.INFO,
    )

    await update.message.reply_text(
        "⚔️ Katana (AI Chat Mode) is online. Send me a message and I'll try to respond using OpenAI."
    )

    log_event(
        logger,
        "bot.command.start.completed",
        body={"user_id": str(user_id), "message": "Welcome message sent"},
        severity=SeverityNumber.DEBUG,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles non-command text messages by sending them to OpenAI GPT."""
    tracer = get_tracer(__name__)
    user_id = update.effective_user.id if update.effective_user else "UnknownUser"

    with tracer.start_as_current_span("bot.handle_message") as span:
        span.set_attribute("user.id", str(user_id))

        if not update.message or not update.message.text:
            log_event(
                logger,
                "bot.message.empty",
                body={"user_id": str(user_id), "message": "Empty or no-text message received, ignoring."},
                severity=SeverityNumber.DEBUG,
            )
            span.set_attribute("message.empty", True)
            return

        user_text = update.message.text
        span.set_attribute("message.length", len(user_text))

        log_event(
            logger,
            "bot.message.received",
            body={
                "user_id": str(user_id),
                "message_preview": f"{user_text[:100]}...",
                "message_length": len(user_text),
            },
            severity=SeverityNumber.INFO,
        )

        if not client:
            log_event(
                logger,
                "bot.error.openai_client_missing",
                body={"user_id": str(user_id), "message": "OpenAI client not initialized."},
                severity=SeverityNumber.ERROR,
            )
            await update.message.reply_text(
                "I apologize, but my connection to the AI core (OpenAI) is not configured. Please contact the administrator."
            )
            span.set_status(trace.Status(trace.StatusCode.ERROR, "OpenAI client not initialized"))
            return

        try:
            log_unstructured_message(logger, f"Sending to OpenAI for user {user_id}...")

            with tracer.start_as_current_span("openai.call") as openai_span:
                start_time = monotonic()
                completion = client.chat.completions.create(
                    model="gpt-4", messages=[{"role": "user", "content": user_text}]
                )
                duration_ms = (monotonic() - start_time) * 1000
                ai_reply = completion.choices[0].message.content.strip()

                openai_span.set_attribute("response.length", len(ai_reply))
                openai_span.set_attribute("duration_ms", duration_ms)

            log_event(
                logger,
                "bot.openai.response.success",
                body={
                    "user_id": str(user_id),
                    "response_preview": f"{ai_reply[:100]}...",
                    "response_length": len(ai_reply),
                    "duration_ms": round(duration_ms),
                    "success": True,
                },
                severity=SeverityNumber.INFO,
            )
            await update.message.reply_text(ai_reply)
            span.set_status(trace.StatusCode.OK)

        except (AuthenticationError, RateLimitError, APIError) as e:
            error_type = type(e).__name__
            log_event(
                logger,
                f"bot.error.openai.{error_type.lower()}",
                body={
                    "user_id": str(user_id),
                    "message": str(e),
                    "error_type": error_type,
                    "success": False,
                },
                severity=SeverityNumber.ERROR,
            )
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"OpenAI Error: {e}"))
            # Choose user message based on error type
            user_message = "An unexpected error occurred."
            if isinstance(e, AuthenticationError):
                user_message = "Error: OpenAI authentication failed. Please contact the administrator."
            elif isinstance(e, RateLimitError):
                 user_message = "Error: OpenAI rate limit exceeded. Please try again later."
            elif isinstance(e, APIError):
                 user_message = f"An error occurred with the OpenAI API: {str(e)}"
            await update.message.reply_text(user_message)

        except Exception as e:
            log_event(
                logger,
                "bot.error.unexpected",
                body={
                    "user_id": str(user_id),
                    "message": "An unexpected error occurred in handle_message.",
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "traceback": traceback.format_exc(),
                    "success": False,
                },
                severity=SeverityNumber.ERROR,
            )
            await update.message.reply_text("Sorry, an unexpected error occurred while processing your message.")
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Unexpected Error: {e}"))


# --- Main Bot Setup ---
def main():
    """Starts the bot."""
    logger_provider = setup_telemetry(service_name="katana-bot")

    global logger
    logger = get_logger("KatanaBotAI")
    tracer = get_tracer(__name__)

    try:
        with tracer.start_as_current_span("bot.main"):
            if OPENAI_API_KEY:
                log_unstructured_message(logger, f"OpenAI client initialized.")
            else:
                log_unstructured_message(logger, "OPENAI_API_KEY not found, OpenAI features will be disabled.", SeverityNumber.WARN)

            if not TELEGRAM_TOKEN:
                log_unstructured_message(logger, "FATAL: KATANA_TELEGRAM_TOKEN not set. Bot cannot start.", SeverityNumber.FATAL)
                return
            if not OPENAI_API_KEY:
                log_unstructured_message(logger, "CRITICAL: OPENAI_API_KEY not set. Message handling will fail.", SeverityNumber.FATAL)


            log_unstructured_message(logger, "Initializing Katana Telegram Bot (AI Chat Mode)...")

            application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            log_unstructured_message(logger, "Katana Bot is running. Press Ctrl-C to stop.", SeverityNumber.INFO)

            application.run_polling()

    except Exception as e_poll:
        log_event(
            logger,
            "bot.error.polling",
            body={
                "message": "A critical error occurred during bot operation.",
                "error_details": str(e_poll),
                "traceback": traceback.format_exc(),
            },
            severity=SeverityNumber.FATAL,
        )
    finally:
        log_unstructured_message(logger, "Katana Bot shutting down.", SeverityNumber.INFO)
        if logger_provider:
            logger_provider.shutdown()


if __name__ == "__main__":
    from time import monotonic
    main()
