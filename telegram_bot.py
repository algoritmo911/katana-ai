# telegram_bot.py
import logging
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
    """Handles general messages from the user."""
    message_text = update.message.text
    user = update.effective_user
    logger.info(f"Received message from {user.username} (ID: {user.id}): {message_text}")

    response_message = ""
    try:
        intent, params = nlp_module.recognize_intent(message_text)
        logger.debug(f"NLP result: intent='{intent}', params={params}")

        if intent == "run_command":
            katana_command = params.get("command")
            if katana_command:
                # For /run, the command string itself is the primary argument to Katana
                # We pass the raw command string to katana_agent, which might parse it further
                # or treat it as an executable string.
                # The current katana_agent.execute_command might need adjustment if it expects
                # specific command keywords vs. arbitrary strings from /run.
                # For now, we'll pass it as is. If katana_agent has a specific handler for "uptime"
                # that's fine, otherwise it might go to a generic handler or fail.
                # Let's assume for /run, the command is the primary thing.
                # We can use a convention like "execute_raw" or pass it as a special param.
                # For now, sending the command string directly.
                # Consider if `/run uptime` should map to `katana_agent.execute_command("uptime")`
                # or `katana_agent.execute_command("run", {"actual_command": "uptime"})`
                # The nlp_module currently returns intent "run_command" and param {"command": "uptime"}
                # Let's make katana_agent handle "run_command" intent.
                # No, katana_agent should receive the actual command to run.
                # So if intent is "run_command", the command for Katana is params["command"].
                response_message = katana_agent.execute_command(katana_command, params)
            else:
                response_message = "Please specify a command to run with /run. Usage: /run <command>"
        elif intent == "get_uptime":
            response_message = katana_agent.execute_command("uptime", params)
        elif intent == "get_status":
            response_message = katana_agent.execute_command("get_status", params)
        elif intent == "greet_user":
            response_message = katana_agent.execute_command("greet_user", params)
        elif intent is None:
            response_message = f"Sorry, I couldn't understand: '{message_text}'. Try `/help`."
        else:
            # Should not happen if NLP module is well-defined
            response_message = f"I understood the intent as '{intent}', but I don't know how to handle it yet."
            logger.warning(f"Unhandled recognized intent: {intent} for message: {message_text}")

    except Exception as e:
        logger.error(f"Error processing message from {user.username}: {message_text}. Error: {e}", exc_info=True)
        response_message = "Sorry, something went wrong while processing your request."

    await update.message.reply_text(response_message)

async def run_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /run command and executes the arguments in Katana."""
    user = update.effective_user
    command_parts = context.args

    logger.info(f"User {user.username} (ID: {user.id}) issued /run command with args: {command_parts}")

    if not command_parts:
        await update.message.reply_text("Please specify a command to run. Usage: `/run <command_text>`")
        return

    katana_command_text = " ".join(command_parts)
    response_message = ""
    try:
        # Here, the `katana_command_text` is what the user typed after /run
        # We pass this directly to the katana_agent.
        # The `params` argument could be used if we wanted to pass additional context,
        # but for /run, the command_text is the main payload.
        logger.info(f"Executing Katana command from /run: '{katana_command_text}'")
        response_message = katana_agent.execute_command(katana_command_text, params={"source": "/run command"})
    except Exception as e:
        logger.error(f"Error executing /run command '{katana_command_text}' for {user.username}: {e}", exc_info=True)
        response_message = f"Sorry, an error occurred while trying to run the command: `{katana_command_text}`."

    await update.message.reply_text(response_message)

def main() -> None:
    """Starts the Telegram bot."""
    logger.info("Starting Telegram bot...")

    if config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please update your .env file or environment variable.")
        print("Error: TELEGRAM_BOT_TOKEN is not set. The bot cannot start.")
        print("Please create a .env file with your token or set the environment variable.")
        print("Example .env file content:\nTELEGRAM_BOT_TOKEN=\"123456:ABC-DEF1234ghIkl-zyx57W2v1uT0\"")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("run", run_command_handler, block=False)) # block=False for async

    # Message handler for general messages (that are not commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram bot polling started.")
    application.run_polling()

if __name__ == '__main__':
    main()
