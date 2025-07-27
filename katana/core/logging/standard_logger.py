import logging
import logging.config
import os
import json
from functools import wraps
import datetime

def setup_logging(log_level="INFO", log_to_file=False, log_file_path="logs/katana.log"):
    """
    Set up logging for the Katana application.
    """
    if log_to_file:
        if not os.path.exists(os.path.dirname(log_file_path)):
            os.makedirs(os.path.dirname(log_file_path))

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "[%(asctime)s] [%(name)s] [%(levelname)s] — %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": log_level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    }

    if log_to_file:
        LOGGING_CONFIG["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": log_file_path,
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "level": log_level,
        }
        LOGGING_CONFIG["root"]["handlers"].append("file")

    logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name):
    """
    Get a logger instance.
    """
    return logging.getLogger(name)


def log_command_trace(logger):
    """
    A decorator to log the entry and exit of a function.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Entering: {func.__name__} with args: {args} and kwargs: {kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Exiting: {func.__name__} with result: {result}")
                return result
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
                raise

        return wrapper

    return decorator
