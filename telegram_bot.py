# telegram_bot.py
import logging
import sys
import config
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import nlp_module # To be used later
import katana_agent # To be used later

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=config.LOG_LEVEL,
    handlers=[
        logging.FileHandler(config.LOG_FILE_TELEGRAM),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    logger.info(f"User {user.username} (ID: {user.id}) started the bot.")
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=None # Can add a ReplyKeyboardMarkup here for quick commands
    )
    await help_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message when the /help command is issued."""
    logger.info(f"User {update.effective_user.username} (ID: {update.effective_user.id}) requested help.")
    help_text = (
        "I can help you interact with the Katana system.\n\n"
        "You can use commands like:\n"
        "`/run <command_for_katana>` - to execute a command on Katana (e.g., `/run uptime`).\n"
        "You can also try natural language like:\n"
        "- 'What is the system uptime?'\n"
        "- 'Greet John'\n\n"
        "Use `/help` to see this message again."
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles general messages from the user by interpreting intent."""
    message_text = update.message.text
    user = update.effective_user
    logger.info(f"Received message from {user.username} (ID: {user.id}): {message_text}")

    response_message = "Sorry, something went wrong."
    try:
        intent, params = nlp_module.recognize_intent(message_text)
        logger.debug(f"NLP result: intent='{intent}', params={params}")

        if intent:
            # Map intent to a command for the Predictive Engine
            command_map = {
                "get_uptime": "uptime",
                "greet_user": "greet_user",
                "run_command": params.get("command")
            }
            katana_command = command_map.get(intent)

            if katana_command:
                # Execute command and get structured response
                advisor_response = katana_agent.execute_command(katana_command, params)
                response_message = advisor_response.get("message", "No message received.")
            else:
                response_message = f"I understood '{intent}', but I don't know what to do."
                logger.warning(f"No command mapping for intent: {intent}")
        else:
            response_message = f"Sorry, I couldn't understand: '{message_text}'. Try `/help`."

    except Exception as e:
        logger.error(f"Error processing message from {user.username}: {e}", exc_info=True)
        response_message = "An error occurred. Please try again later."

    await update.message.reply_text(response_message)


async def run_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /run command for direct execution."""
    user = update.effective_user
    command_parts = context.args
    logger.info(f"User {user.username} (ID: {user.id}) issued /run command with args: {command_parts}")

    if not command_parts:
        await update.message.reply_text("Usage: `/run <command_text>`")
        return

    katana_command_text = " ".join(command_parts)
    response_message = "An error occurred while running the command."
    try:
        logger.info(f"Executing direct command from /run: '{katana_command_text}'")
        # The `execute_command` now returns a dictionary
        advisor_response = katana_agent.execute_command(
            katana_command_text,
            params={"source": "/run command", "user": user.username}
        )
        # Extract the message to be sent to the user
        response_message = advisor_response.get("message", "No response message from Katana.")

    except Exception as e:
        logger.error(f"Error executing /run command '{katana_command_text}' for {user.username}: {e}", exc_info=True)
        response_message = f"Sorry, an error occurred while trying to run the command: `{katana_command_text}`."

    await update.message.reply_text(response_message)

def main() -> None:
    """Initializes and starts the Telegram bot."""
    logger.info("Initializing Telegram bot...")

    # Ensure the bot token is set
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.critical("TELEGRAM_BOT_TOKEN is not configured. The bot cannot start.")
        print("FATAL: TELEGRAM_BOT_TOKEN is missing. Please check your .env file or environment variables.", file=sys.stderr)
        return

    # Initialize the bot application
    try:
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("run", run_command_handler, block=False))

        # Register message handler for non-command text
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start polling for updates
        logger.info("Telegram bot is now polling for updates.")
        application.run_polling()

    except Exception as e:
        logger.critical(f"Failed to initialize or run the bot: {e}", exc_info=True)
        print(f"FATAL: An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
