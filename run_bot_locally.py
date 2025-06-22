import os
import logging
import time
from dotenv import load_dotenv # Using python-dotenv to load .env file for convenience

# Configure basic logging for this script to see startup messages from the bot module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_local_bot_instance():
    """
    Sets up environment variables (if not already set) and runs the KatanaBot.
    This script is for local testing and liveness checks.
    """
    logger.info("--- Starting local KatanaBot instance via run_bot_locally.py ---")

    # Load .env file if it exists, for convenience in local development
    # Create a .env file in the root with your tokens if you don't want to set them globally
    # Example .env content:
    # KATANA_TELEGRAM_TOKEN="your_telegram_token"
    # ANTHROPIC_API_KEY="your_anthropic_key"
    # OPENAI_API_KEY="your_openai_key"
    load_dotenv()
    logger.info(f".env loaded: {load_dotenv()}")


    # --- Set default mock tokens if not found in environment ---
    # This allows the script to run without a .env file or pre-set env vars,
    # though the bot will use dummy keys and might not fully function with actual Telegram.
    if not os.getenv('KATANA_TELEGRAM_TOKEN'):
        logger.warning("KATANA_TELEGRAM_TOKEN not found in env, using a mock token for this local run.")
        os.environ['KATANA_TELEGRAM_TOKEN'] = "123456:ABCDEFGHIKLMNOPQRSTUVWXYZ123456789" # Valid format, but mock

    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.info("ANTHROPIC_API_KEY not found in env, bot will use its internal default dummy key.")
        # Bot has its own default "dummy_anthropic_key_env", so no need to set another one here
        # unless we want to override that default specifically for this script.

    if not os.getenv('OPENAI_API_KEY'):
        logger.info("OPENAI_API_KEY not found in env, bot will use its internal default dummy key.")
        # Bot has its own default "dummy_openai_key_env"

    logger.info("Environment variables prepared (or defaults will be used by bot).")
    logger.info(f"KATANA_TELEGRAM_TOKEN: {os.getenv('KATANA_TELEGRAM_TOKEN')[:10]}...") # Log a snippet
    logger.info(f"ANTHROPIC_API_KEY: {os.getenv('ANTHROPIC_API_KEY')}")
    logger.info(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")

    try:
        # Important: Import katana_bot *after* os.environ might have been modified
        from bot import katana_bot

        logger.info("KatanaBot module imported. Calling main()...")
        # The bot will run indefinitely due to polling(none_stop=True)
        # To test "liveness", you'd typically run this, see startup logs,
        # maybe send a message from a real Telegram client if token is real,
        # and then manually stop this script (Ctrl+C).
        katana_bot.main()

    except ValueError as ve:
        logger.error(f"ValueError during bot startup: {ve}")
        logger.error("This usually means the Telegram token is invalid or missing even after attempting to set a mock one.")
    except ImportError:
        logger.error("Failed to import katana_bot. Ensure it's in the PYTHONPATH or run from the project root.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred while trying to run the bot: {e}", exc_info=True)

if __name__ == '__main__':
    run_local_bot_instance()
    # The script will hang here if bot.polling() is running, until manually stopped.
    # If katana_bot.main() were to finish (e.g. polling error not caught, or finite polling),
    # this script would then exit.
    logger.info("--- run_bot_locally.py script finished or bot was stopped. ---")
