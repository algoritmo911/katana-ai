import logging
import os
from logging.handlers import RotatingFileHandler

# Define the location for logs within the main project structure
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE_PATH = os.path.join(LOG_DIR, "self_healing.log")

# Configure the logger
logger = logging.getLogger("SelfHealingModule")
logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels of messages

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s')

# Create a file handler (RotatingFileHandler for managing log file size)
# Rotates when the log file reaches 2MB, keeps up to 5 backup logs.
file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=2*1024*1024, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Create a console handler (optional, for also printing logs to stdout)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Or DEBUG, depending on verbosity needed in console
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent logging from propagating to the root logger, if this module's logging is meant to be self-contained.
# logger.propagate = False

if __name__ == "__main__":
    # Example usage:
    logger.debug("This is a debug message from self_healing_logger.")
    logger.info("This is an info message from self_healing_logger.")
    logger.warning("This is a warning message from self_healing_logger.")
    logger.error("This is an error message from self_healing_logger.")
    logger.critical("This is a critical message from self_healing_logger.")
    print(f"Self-healing module logs are being written to: {LOG_FILE_PATH}")
