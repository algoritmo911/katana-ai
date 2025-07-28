import logging
import os
from logging.handlers import RotatingFileHandler

def get_logger(name: str, level: str = None, log_file: str = None) -> logging.Logger:
    """
    Creates and configures a logger.

    Args:
        name (str): The name of the logger.
        level (str, optional): The logging level. Defaults to None, in which case it is read from the LOG_LEVEL environment variable.
        log_file (str, optional): The path to the log file. Defaults to None, in which case it is read from the LOG_FILE_PATH environment variable.

    Returns:
        logging.Logger: The configured logger.
    """
    log_level_str = level or os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Prevent duplicate handlers if the logger is already configured
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file_path = log_file or os.getenv('LOG_FILE_PATH')
    if log_file_path:
        try:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            # Use RotatingFileHandler to prevent log files from growing indefinitely
            file_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5, mode='a', encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file enabled: {log_file_path}")
        except Exception as e:
            logger.error(f"Failed to configure file logging to {log_file_path}: {e}", exc_info=True)

    return logger
