import logging
import logging.handlers

# Define the default logger name
DEFAULT_LOGGER_NAME = 'katana_logger'
DEFAULT_LOG_FILE_NAME = 'katana_events.log'
MAX_BYTES = 1 * 1024 * 1024  # 1MB
BACKUP_COUNT = 5

def setup_logging(log_level=logging.INFO, log_file_path=None):
    """
    Configures the logging for the Katana application.

    Args:
        log_level (int, optional): The logging level to set for the logger.
                                   Defaults to logging.INFO.
        log_file_path (str, optional): Path to the log file.
                                       Defaults to DEFAULT_LOG_FILE_NAME.
    """
    logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    logger.setLevel(log_level)

    # Remove existing handlers to prevent duplication if called multiple times
    if logger.hasHandlers():
        for handler in list(logger.handlers): # Iterate over a copy
            logger.removeHandler(handler)
            handler.close() # Close handler before removing

    # Define log format
    log_format = '%(levelname)s %(asctime)s - %(module)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Create console handler
    console_handler = logging.StreamHandler() # Outputs to stderr by default
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Determine log file path
    actual_log_file_path = log_file_path if log_file_path else DEFAULT_LOG_FILE_NAME

    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        actual_log_file_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Do not log "Logging setup complete." here as it might interfere with tests
    # or be undesirable if setup_logging is called multiple times.
    # Let the application log its first message.

def get_logger(name=None):
    """
    Returns a logger instance.

    Args:
        name (str, optional): The name of the logger.
                              Defaults to the DEFAULT_LOGGER_NAME.

    Returns:
        logging.Logger: The logger instance.
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger(DEFAULT_LOGGER_NAME)

if __name__ == '__main__':
    # Example usage:
    # Call setup_logging() once when your application starts.
    # This example will now use the defaults defined in setup_logging.
    setup_logging(log_level=logging.DEBUG) # log_file_path will be 'katana_events.log'

    # Get the logger in different modules
    logger1 = get_logger() # This gets 'katana_logger'
    logger2 = get_logger("katana.module2") # Example for another module

    logger1.debug("This is a debug message from the default logger.")
    logger1.info("This is an info message from the default logger.")
    logger1.warning("This is a warning message from the default logger.")
    # Example of a specific module logger
    logger2.info("This is an info message from katana.module2.") # This logger is not katana_logger, so it won't have handlers unless configured separately.
                                                              # For it to use katana_logger's handlers, it should be a child e.g. get_logger(DEFAULT_LOGGER_NAME + ".module2")
                                                              # or rely on propagation to the root logger if katana_logger is the root (which it isn't here).
                                                              # For simplicity, this example will just show it doesn't automatically use katana_logger's config.
                                                              # To make it work as part of katana_logger, use get_logger().getChild("module2") or get_logger("katana_logger.module2")

    # To demonstrate logger2 using the setup:
    logger_mod2 = get_logger(DEFAULT_LOGGER_NAME + ".module2") # Child logger
    logger_mod2.info("This info message from module2 WILL appear via katana_logger config.")


    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger1.error("Error dividing by zero!", exc_info=True) # This will use katana_logger

    # The print statement for log file location might be misleading if log_file_path is customized.
    # Commenting out, as one should know the log path from configuration.
    # print(f"Log file is at: {DEFAULT_LOG_FILE_NAME}") # Or actual_log_file_path if it were accessible here
