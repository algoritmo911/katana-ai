import os
import logging
import threading
import time
from datetime import datetime, timezone
from typing import List, Dict

# Logger for this module
logger = logging.getLogger(__name__)

# --- Heartbeat Functionality ---
# This can remain here as a utility if main.py decides to use it.
_heartbeat_thread = None
_heartbeat_stop_event = threading.Event()

def _write_heartbeat(file_path: str):
    """Writes/updates the heartbeat file with the current timestamp."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(datetime.now(timezone.utc).isoformat())
    except Exception as e:
        logger.error(f"Failed to write heartbeat to {file_path}: {e}", exc_info=True)

def _heartbeat_loop(file_path: str, interval: int):
    """Periodically writes a heartbeat to the specified file."""
    logger.info(f"Heartbeat thread started. Updating {file_path} every {interval} seconds.")
    while not _heartbeat_stop_event.is_set():
        _write_heartbeat(file_path)
        _heartbeat_stop_event.wait(interval)
    logger.info("Heartbeat thread stopped.")

def start_heartbeat_thread():
    """Starts the global heartbeat thread if configured and not already running."""
    global _heartbeat_thread
    if _heartbeat_thread is not None and _heartbeat_thread.is_alive():
        logger.warning("Heartbeat thread already running.")
        return

    heartbeat_file = os.getenv('HEARTBEAT_FILE_PATH')
    heartbeat_interval_str = os.getenv('HEARTBEAT_INTERVAL_SECONDS', '30')

    if not heartbeat_file:
        logger.info("HEARTBEAT_FILE_PATH not set. Heartbeat thread will not start.")
        return

    try:
        heartbeat_interval = int(heartbeat_interval_str)
        if heartbeat_interval <= 0:
            raise ValueError("Heartbeat interval must be positive.")
    except ValueError:
        logger.error(f"Invalid HEARTBEAT_INTERVAL_SECONDS: '{heartbeat_interval_str}'. Must be positive. Heartbeat disabled.", exc_info=True)
        return

    _heartbeat_stop_event.clear()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, args=(heartbeat_file, heartbeat_interval), daemon=True)
    _heartbeat_thread.start()

def stop_heartbeat_thread():
    """Stops the global heartbeat thread."""
    global _heartbeat_thread
    if _heartbeat_thread and _heartbeat_thread.is_alive():
        logger.info("Stopping heartbeat thread...")
        _heartbeat_stop_event.set()
        _heartbeat_thread.join(timeout=5)
        if _heartbeat_thread.is_alive():
            logger.warning("Heartbeat thread did not stop in time.")
        _heartbeat_thread = None
    else:
        logger.info("Heartbeat thread not running or already stopped.")

# --- Placeholder for NLP Model Interaction ---
# This is the original synchronous placeholder.
# main.py currently uses its own async placeholder (get_katana_response_async).
# This can be kept if needed, or main.py's version can be moved here and made configurable.
def get_katana_response(history: List[Dict[str, str]]) -> str:
    """Synchronous placeholder for function getting response from NLP model."""
    logger.info(f"Original get_katana_response (sync) called with history: {history}")
    if not history:
        return "Катана к вашим услугам. О чём поразмыслим? (sync placeholder)"
    last_message = history[-1]['content']
    return f"Размышляю над вашим последним сообщением: '{last_message}'... (это синхронная заглушка из katana_bot.py)"

# --- Constants (if needed by other modules, though main.py redefines them) ---
# MESSAGE_ROLE_USER = "user"
# MESSAGE_ROLE_ASSISTANT = "assistant"
# COMMAND_FILE_DIR can be defined in main.py or a config module.

# --- Old Telegram-specific logic, command handlers, and main polling loop have been removed ---
# The core application logic is now in main.py's `process_user_message` and `run` functions.
# API token loading and telebot instance are handled by TelegramInterface.

logger.info("katana_bot.py loaded (now primarily a utility module).")

# No if __name__ == '__main__' block for direct execution of bot polling from here.
# run_bot_locally.py or the new main.py is the entry point.