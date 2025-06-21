import logging
import logging.handlers

# Define the default logger name
DEFAULT_LOGGER_NAME = 'katana_logger'
DEFAULT_LOG_FILE_NAME = 'katana_events.log'
MAX_BYTES = 1 * 1024 * 1024  # 1MB
BACKUP_COUNT = 5

# Define a new type for module_levels for clarity
ModuleLogLevels = Optional[Dict[str, int]]

def setup_logging(
    log_level: int = logging.INFO,
    log_file_path: Optional[str] = None,
    module_levels: ModuleLogLevels = None
):
    """
    Configures the logging for the Katana application.

    Args:
        log_level (int, optional): The default logging level for the main logger.
                                   Defaults to logging.INFO.
        log_file_path (str, optional): Path to the log file.
                                       Defaults to DEFAULT_LOG_FILE_NAME.
        module_levels (Dict[str, int], optional): A dictionary mapping module
                                                  names to specific log levels.
    """
    # Configure the main Katana logger
    main_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    main_logger.setLevel(log_level) # Set default level for the main logger

    # Remove existing handlers from the main logger to prevent duplication
    if main_logger.hasHandlers():
        for handler in list(main_logger.handlers): # Iterate over a copy
            main_logger.removeHandler(handler)
            handler.close() # Close handler before removing

    # Define log format
    log_format = '%(levelname)s %(asctime)s - %(name)s - %(message)s' # Changed module to name for better clarity
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Create console handler for the main logger
    console_handler = logging.StreamHandler() # Outputs to stderr by default
    console_handler.setFormatter(formatter)
    main_logger.addHandler(console_handler)

    # Determine log file path
    actual_log_file_path = log_file_path if log_file_path else DEFAULT_LOG_FILE_NAME

    # Create file handler with rotation for the main logger
    file_handler = logging.handlers.RotatingFileHandler(
        actual_log_file_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    main_logger.addHandler(file_handler)

    # Configure specific log levels for other modules
    if module_levels:
        for module_name, level in module_levels.items():
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(level)
            # If these modules should also output to the main logger's handlers,
            # ensure they propagate (which is by default true) and do not have their own handlers
            # that stop propagation. Or, explicitly add main_logger's handlers to them (less common).

def add_filter_to_main_logger(filter_instance: logging.Filter):
    """
    Adds a filter to all handlers of the main Katana logger.

    Args:
        filter_instance (logging.Filter): The filter object to add.
    """
    main_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    for handler in main_logger.handlers:
        handler.addFilter(filter_instance)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger instance. If no name is provided, returns the main Katana logger.
    If a name is provided, it returns a logger with that name, which will typically
    be a child of the main Katana logger if named like 'katana_logger.child_module'.

    Args:
        name (str, optional): The name of the logger.
                              If None, returns the main Katana logger.
                              To get a child logger that inherits handlers from
                              the main Katana logger, use a name like
                              f"{DEFAULT_LOGGER_NAME}.your_module_name".

    Returns:
        logging.Logger: The logger instance.
    """
    return logging.getLogger(name if name else DEFAULT_LOGGER_NAME)


# Example custom filter
class KeywordFilter(logging.Filter):
    def __init__(self, keyword: str):
        super().__init__()
        self.keyword = keyword.lower()

    def filter(self, record: logging.LogRecord) -> bool:
        return self.keyword not in record.getMessage().lower()


if __name__ == '__main__':
    # --- Basic Setup ---
    # Set the default level for katana_logger to INFO.
    # Set specific levels for child/other modules.
    module_config = {
        f"{DEFAULT_LOGGER_NAME}.module1": logging.DEBUG, # Will show DEBUG and above for this module
        f"{DEFAULT_LOGGER_NAME}.module2": logging.WARNING, # Will show WARNING and above for this module
        "external_lib": logging.CRITICAL # Example for a non-katana_logger related module
    }
    setup_logging(log_level=logging.INFO, module_levels=module_config)

    # --- Get Loggers ---
    # Main katana logger
    main_katana_logger = get_logger() # Gets 'katana_logger'

    # Child loggers of katana_logger
    # These will use katana_logger's handlers and their own specific levels if set.
    module1_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.module1")
    module2_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.module2")
    module3_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.module3") # Not in module_config, will use main_katana_logger's level (INFO)

    # Another logger, not part of katana_logger hierarchy directly
    # This logger ('external_lib') will have its level set to CRITICAL.
    # Its output will go to the root logger's handlers (if any) or stderr by default if root has no handlers.
    # Since setup_logging() only configures 'katana_logger' and its children,
    # 'external_lib' logs might not appear in 'katana_events.log' unless the root logger is also configured.
    # For this example, we'll assume it might print to console if root logger is basicConfig'd by default.
    external_logger = get_logger("external_lib")


    # --- Log some messages (before filter) ---
    print("\n--- Logging before filter ---")
    main_katana_logger.debug("This is a DEBUG message from main_katana_logger. (Should not see if level is INFO)")
    main_katana_logger.info("This is an INFO message from main_katana_logger.")

    module1_logger.debug("Module1: DEBUG message. (Should see as its level is DEBUG)")
    module1_logger.info("Module1: INFO message.")

    module2_logger.info("Module2: INFO message. (Should not see as its level is WARNING)")
    module2_logger.warning("Module2: WARNING message.")

    module3_logger.debug("Module3: DEBUG message. (Should not see as it inherits INFO from main_katana_logger)")
    module3_logger.info("Module3: INFO message.")

    external_logger.warning("ExternalLib: WARNING message. (Should not see as its level is CRITICAL)")
    external_logger.critical("ExternalLib: CRITICAL message.")


    # --- Add a filter ---
    print("\n--- Adding filter to EXCLUDE messages containing 'secret' ---")
    keyword_filter = KeywordFilter("secret")
    add_filter_to_main_logger(keyword_filter) # Adds filter to katana_logger's handlers

    # --- Log some messages (after filter) ---
    print("\n--- Logging after filter ---")
    main_katana_logger.info("This is an INFO message from main_katana_logger, without the keyword.")
    main_katana_logger.info("This is a SECRET INFO message from main_katana_logger. (Should be filtered out)")

    module1_logger.debug("Module1: DEBUG message, without the keyword.")
    module1_logger.debug("Module1: This is a SECRET DEBUG message. (Should be filtered out)")

    module2_logger.warning("Module2: WARNING message, without the keyword.")
    module2_logger.warning("Module2: This is a SECRET WARNING message. (Should be filtered out)")

    module3_logger.info("Module3: INFO message, without the keyword.")
    module3_logger.info("Module3: This is a SECRET INFO message. (Should be filtered out)")

    # Note: The filter is added to katana_logger's handlers.
    # Messages from external_logger are not processed by katana_logger's handlers,
    # so they won't be affected by this filter directly.
    # If external_logger's messages were to propagate to the root logger, and if the root logger
    # also had handlers that were given this filter, then it would apply.
    # Our current add_filter_to_main_logger is specific to DEFAULT_LOGGER_NAME.
    external_logger.critical("ExternalLib: CRITICAL message, without the keyword.")
    external_logger.critical("ExternalLib: This is a SECRET CRITICAL message. (Should NOT be filtered by this setup)")

    print(f"\nCheck '{DEFAULT_LOG_FILE_NAME}' for file output.")
    print("Note: 'external_lib' logs might only appear on console if root logger has default handlers and level allows.")
