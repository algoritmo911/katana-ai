import asyncio
import logging
import os
import threading
import time
from dotenv import load_dotenv

# --- 1. Initial Setup: Logging and Environment Variables ---
def setup_logging():
    """Configures logging for the entire application."""
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file_path = os.getenv('LOG_FILE_PATH')
    if log_file_path:
        try:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logging.getLogger().addHandler(file_handler)
            logging.info(f"✅ Logging to file enabled: {log_file_path}")
        except Exception as e:
            logging.error(f"❌ Failed to configure file logging to {log_file_path}: {e}", exc_info=True)

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

from src.orchestrator.task_orchestrator import TaskOrchestrator
from src.agents.julius_agent import JuliusAgent
from bot.katana_bot import bot, init_dependencies, start_heartbeat_thread, stop_heartbeat_thread

# --- 2. Configuration from Environment ---
ROUND_INTERVAL_SECONDS = 5
ORCHESTRATOR_LOG_FILE = "orchestrator_log.json"
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
TASK_QUEUE_NAME = os.getenv('REDIS_TASK_QUEUE_NAME', 'katana:task_queue')

# --- 3. Global Shutdown Event ---
stop_event = threading.Event()

# --- 4. Orchestrator and Bot Runner Functions ---

async def run_orchestrator_loop(orchestrator: TaskOrchestrator):
    """The main async loop for the task orchestrator."""
    logger.info(f"Orchestrator is now monitoring Redis queue '{TASK_QUEUE_NAME}' for tasks.")
    try:
        while not stop_event.is_set():
            await orchestrator.run_round()
            await asyncio.sleep(ROUND_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logger.info("Orchestrator loop cancelled.")
    finally:
        logger.info("Orchestrator loop stopped.")

def run_bot_polling_blocking():
    """This is the blocking call to start the bot."""
    logger.info("Starting bot polling...")
    bot.polling(none_stop=True, interval=1)
    logger.info("Bot polling has stopped.")

async def main():
    """Initializes and runs all components of the Katana application."""
    logger.info("🚀 Initializing Katana AI...")

    # --- 5. Initialize Components ---
    init_dependencies()
    julius_agent = JuliusAgent()
    try:
        orchestrator = TaskOrchestrator(
            agent=julius_agent,
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            redis_db=REDIS_DB,
            redis_password=REDIS_PASSWORD,
            task_queue_name=TASK_QUEUE_NAME,
            metrics_log_file=ORCHESTRATOR_LOG_FILE
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize TaskOrchestrator: {e}", exc_info=True)
        return

    # --- 6. Start Concurrent Tasks ---
    loop = asyncio.get_running_loop()
    start_heartbeat_thread()
    orchestrator_task = loop.create_task(run_orchestrator_loop(orchestrator))
    bot_polling_task = loop.run_in_executor(None, run_bot_polling_blocking)

    logger.info("✅ Katana AI is now fully operational.")

    try:
        await asyncio.gather(orchestrator_task, bot_polling_task)
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    finally:
        logger.info("Initiating shutdown sequence...")
        stop_heartbeat_thread()
        bot.stop_polling()
        logger.info("Bot polling stop signal sent.")
        orchestrator_task.cancel()
        await asyncio.sleep(1)
        logger.info("🛑 Katana AI has shut down.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🤖 Shutdown requested by user (Ctrl+C).")
    finally:
        stop_event.set()
        time.sleep(1)
        logger.info("Application exit.")
        os._exit(0)
