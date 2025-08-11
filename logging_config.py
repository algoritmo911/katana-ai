import logging
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def setup_logging(log_level=logging.INFO):
    """Configures basic logging with a file and console handler."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger("katana")  # Get a specific logger instance
    logger.setLevel(log_level)

    # Prevent adding multiple handlers if called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File Handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.info("Logging setup complete. Logging to console and %s", LOG_FILE)
    return logger


if __name__ == "__main__":
    # Example usage:
    setup_logging(logging.DEBUG)
    main_logger = logging.getLogger("katana")
    main_logger.debug("This is a debug message from logging_config.")
    main_logger.info("This is an info message from logging_config.")
    main_logger.warning("This is a warning message from logging_config.")
