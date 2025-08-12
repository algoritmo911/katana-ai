import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "katana.log")

def setup_logging(level="INFO"):
    """
    Set up a centralized, rotating log system for the Katana application.

    This function configures a root logger to ensure that all modules use
    the same logging setup. It includes a rotating file handler to manage

    log file sizes and a stream handler to output logs to the console.

    Args:
        level (str or int): The logging level to set for the logger.
                            Can be "DEBUG", "INFO", "WARNING", "ERROR", etc.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create logs directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Rotating File Handler
    # Creates a new file when the log reaches 5MB, keeps 5 old log files.
    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=1024 * 1024 * 5, backupCount=5
    )
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logging.getLogger('katana').info(
        "Centralized logging setup complete. Logging to console and %s", LOG_FILE
    )
