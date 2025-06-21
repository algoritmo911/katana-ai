import logging
import logging.config
import logging.handlers
from typing import Optional, Dict, Any

# Define the default logger name
DEFAULT_LOGGER_NAME = 'katana_logger'
# Default log file for general events, typically for the DEFAULT_LOGGER_NAME
DEFAULT_LOG_FILE_NAME = 'logs/katana_events.log'
# Standard log rotation parameters
MAX_BYTES = 1 * 1024 * 1024  # 1MB
BACKUP_COUNT = 5

# Define paths for module-specific logs
LOGS_DIR = "logs" # Base directory for all log files
CORE_LOG_FILE = f"{LOGS_DIR}/core.log" # Log file for core module
TRADER_LOG_FILE = f"{LOGS_DIR}/trader.log" # Log file for trader module
VOICE_LOG_FILE = f"{LOGS_DIR}/voice.log" # Log file for voice module
BOT_LOG_FILE = f"{LOGS_DIR}/bot.log" # Log file for bot specific logs

# It's good practice to ensure the log directory exists.
# This can be done here or by a deployment/startup script.
# For example:
# import os
# if not os.path.exists(LOGS_DIR):
#     os.makedirs(LOGS_DIR, exist_ok=True)

# --- Type Aliases for Configuration Clarity ---
# Defines a dictionary mapping module names (strings) to log levels (integers).
ModuleLogLevels = Optional[Dict[str, int]]
# Defines a dictionary for module-specific file handler configurations.
# Keys are module names (e.g., "katana_logger.trader").
# Values are dictionaries specifying 'filename', 'level', 'maxBytes', 'backupCount'.
ModuleFileConfigs = Optional[Dict[str, Dict[str, Any]]]


def setup_logging(
    log_level: int = logging.INFO,
    log_file_path: Optional[str] = None,
    module_levels: ModuleLogLevels = None,
    module_file_configs: ModuleFileConfigs = None
):
    """
    Configures logging for the application using `logging.config.dictConfig`.
    This allows for a structured and flexible logging setup, including:
    - A main logger (`DEFAULT_LOGGER_NAME`) with console and general file output (`katana_events.log`).
    - Module-specific log levels.
    - Dedicated file handlers for specific modules (e.g., trader module logs to `trader.log`).

    Args:
        log_level (int, optional): The default logging level for the `DEFAULT_LOGGER_NAME`.
                                   Defaults to `logging.INFO`.
        log_file_path (str, optional): Path for the main rotating file handler (`katana_events.log`).
                                       Defaults to `DEFAULT_LOG_FILE_NAME`.
        module_levels (Dict[str, int], optional): A dictionary mapping module names to specific
                                                  log levels. This is applied if the module is
                                                  not configured in `module_file_configs`.
        module_file_configs (Dict[str, Dict[str, Any]], optional):
            Configuration for module-specific file handlers. Each key is a logger name
            (e.g., "katana_logger.trader"), and the value is a dictionary with
            handler parameters like "filename", "level", "maxBytes", "backupCount".
            Loggers configured here will also output to the console and will have
            propagation disabled to keep their file logs separate.
            Example:
            {
                "katana_logger.trader": {
                    "filename": TRADER_LOG_FILE, # from constants
                    "level": logging.DEBUG,      # Log level for this specific logger
                    "maxBytes": MAX_BYTES,       # Optional, defaults to global MAX_BYTES
                    "backupCount": BACKUP_COUNT  # Optional, defaults to global BACKUP_COUNT
                }
            }
    """
    actual_log_file_path = log_file_path if log_file_path else DEFAULT_LOG_FILE_NAME

    # Base configuration dictionary for `logging.config.dictConfig`.
    # `version: 1` is required.
    # `disable_existing_loggers: False` ensures that other loggers (e.g., from libraries) are not disabled.
    config: Dict[str, Any] = {
        'version': 1,
        'disable_existing_loggers': False,

        # Formatters define the layout of log records.
        'formatters': {
            # 'standard' formatter is used by all handlers in this configuration.
            # It includes level, timestamp, logger name, and the log message.
            'standard': {
                'format': '%(levelname)s %(asctime)s - %(name)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S', # Timestamp format
            },
        },

        # Handlers define where log messages are sent (e.g., console, files).
        'handlers': {
            # 'console' handler: Outputs log messages to the standard error stream (stderr).
            # Uses the 'standard' formatter.
            # `level: logging.DEBUG` means this handler can process all messages from DEBUG upwards.
            # The effective log level is determined by the logger's level.
            'console': {
                'class': 'logging.StreamHandler', # Logs to a stream (e.g., sys.stderr)
                'formatter': 'standard',
                'level': logging.DEBUG,
            },
            # 'default_file' handler: A rotating file handler for general application events.
            # Logs from `DEFAULT_LOGGER_NAME` and its propagating children go here.
            # Uses `logging.handlers.RotatingFileHandler` to manage log file size and rotation.
            'default_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'filename': actual_log_file_path, # Path to katana_events.log
                'maxBytes': MAX_BYTES,           # Max file size before rotation
                'backupCount': BACKUP_COUNT,     # Number of backup files to keep
                'level': logging.DEBUG,          # Handler processes DEBUG and above
            },
        },

        # Loggers define named logging channels. Applications get loggers by name.
        'loggers': {
            # Configuration for the main application logger (`DEFAULT_LOGGER_NAME`, e.g., 'katana_logger').
            DEFAULT_LOGGER_NAME: {
                'handlers': ['console', 'default_file'], # Uses console and katana_events.log
                'level': log_level,                     # Default log level for this logger
                'propagate': False, # IMPORTANT: Prevents messages sent to this logger from being
                                    # passed to the handlers of its parent (the root logger).
                                    # This is crucial if the root logger is also configured with handlers,
                                    # to avoid duplicate log messages. It also makes this logger a
                                    # distinct endpoint for its children that *do* propagate.
            },
        },
        # Optional: Configure the root logger.
        # The root logger catches all messages from any logger that propagate up to it,
        # if those loggers don't have `propagate: False` and their own handlers.
        # 'root': {
        #     'handlers': ['console'], # Example: send all propagated, unhandled logs to console
        #     'level': logging.WARNING,
        # },
    }

    # --- Process Module-Specific File Configurations ---
    # These modules get their own dedicated log files and also log to the console.
    # Their propagation is set to False to prevent their logs from also going to `default_file` (katana_events.log).
    if module_file_configs:
        for logger_name, file_conf in module_file_configs.items():
            # Create a unique handler name for this module's file logger.
            # e.g., "katana_logger.core" -> "katana_logger_core_file_handler"
            handler_name = f"{logger_name.replace('.', '_')}_file_handler"

            # Define the handler for this module's dedicated log file.
            # It's a RotatingFileHandler, similar to 'default_file'.
            config['handlers'][handler_name] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'filename': file_conf['filename'], # Path to the module's specific log file (e.g., trader.log)
                'maxBytes': file_conf.get('maxBytes', MAX_BYTES), # Use specific or default
                'backupCount': file_conf.get('backupCount', BACKUP_COUNT), # Use specific or default
                'level': file_conf.get('level', logging.DEBUG), # Handler processes messages at this level or above.
                                                                # The logger's level is the final gate.
            }

            # Ensure the logger entry exists in the config.
            if logger_name not in config['loggers']:
                config['loggers'][logger_name] = {}

            # Assign handlers: the new dedicated file handler and the common 'console' handler.
            config['loggers'][logger_name]['handlers'] = ['console', handler_name]
            # Set the logger's effective level. Messages below this level are ignored.
            config['loggers'][logger_name]['level'] = file_conf.get('level', log_level)
            # CRUCIAL: Prevent this logger's messages from propagating to `DEFAULT_LOGGER_NAME`'s handlers.
            # This ensures its file logs are separate and don't also appear in `katana_events.log`.
            config['loggers'][logger_name]['propagate'] = False

    # --- Process General Module-Level Configurations ---
    # These are for modules that don't have dedicated file handlers but need a specific log level.
    # Their logs will propagate to their parent logger (typically `DEFAULT_LOGGER_NAME` if named as children,
    # or the root logger otherwise) and use the parent's handlers.
    if module_levels:
        for module_name, level_val in module_levels.items():
            # Apply only if this logger hasn't been configured by `module_file_configs` already.
            if module_name not in config['loggers']:
                config['loggers'][module_name] = {
                    'level': level_val,
                    # No 'handlers' or 'propagate' specified here means:
                    # - It will use its parent's handlers (due to propagation, which is True by default).
                    # - For example, if `module_name` is "katana_logger.child_module", it will propagate
                    #   to `katana_logger` and use its 'console' and 'default_file' handlers.
                    # - If `module_name` is "some_other_library", it propagates to the root logger.
                }
            # If the logger was configured by `module_file_configs` but a level wasn't specified there,
            # `module_levels` can provide a fallback level.
            elif 'level' not in config['loggers'][module_name]:
                 config['loggers'][module_name]['level'] = level_val

    # Apply the constructed dictionary configuration.
    logging.config.dictConfig(config)

def add_filter_to_main_logger(filter_instance: logging.Filter):
    """
    Adds a filter to all handlers of the main Katana logger (`DEFAULT_LOGGER_NAME`).
    This function assumes `setup_logging` has been called and the logger exists.
    It affects the 'console' and 'default_file' (`katana_events.log`) handlers.

    Args:
        filter_instance (logging.Filter): The filter object to add.
    """
    # This function currently targets DEFAULT_LOGGER_NAME's handlers.
    # For module-specific file handlers (e.g., core.log, trader.log),
    # if they require different filters than those applied to DEFAULT_LOGGER_NAME's handlers,
    # a more generic filter application mechanism or new functions would be needed.
    # For example, `add_filter_to_logger_handlers(logger_name_str, filter_instance)`.
    main_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    if main_logger.handlers:
        for handler in main_logger.handlers:
            handler.addFilter(filter_instance)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger instance configured by `setup_logging` via `dictConfig`.

    - If `name` is `None` or omitted, it returns the main Katana logger (`DEFAULT_LOGGER_NAME`).
      Example: `get_logger()` returns the 'katana_logger'.

    - If `name` is provided (e.g., "katana_logger.core"):
        - If this logger name was configured in `module_file_configs` (e.g., "katana_logger.core"),
          it will use its dedicated file handler (e.g., `core.log`) and the 'console' handler,
          with `propagate: False`.
          Example: `get_logger("katana_logger.core")` for core module logging.

        - If this logger name was configured only in `module_levels` (e.g., "katana_logger.module1"),
          it will have its level set and will propagate to `DEFAULT_LOGGER_NAME`, using
          the 'console' and 'default_file' (`katana_events.log`) handlers.
          Example: `get_logger("katana_logger.module1")`.

        - If the logger name is a child of `DEFAULT_LOGGER_NAME` but not explicitly configured
          (e.g., "katana_logger.propagating_child"), it inherits the level and handlers
          from `DEFAULT_LOGGER_NAME`.
          Example: `get_logger("katana_logger.propagating_child")`.

        - If the logger name is unrelated to `DEFAULT_LOGGER_NAME` (e.g., "external_lib"),
          it will have its level set if specified in `module_levels` and will propagate
          to the root logger. Its output depends on the root logger's configuration.
          Example: `get_logger("external_lib")`.

    Args:
        name (str, optional): The hierarchical name of the logger.
                              Defaults to `DEFAULT_LOGGER_NAME`.

    Returns:
        logging.Logger: The configured logger instance.
    """
    return logging.getLogger(name if name else DEFAULT_LOGGER_NAME)


# Example custom filter: Filters out log records containing a specific keyword.
class KeywordFilter(logging.Filter):
    def __init__(self, keyword: str):
        super().__init__()
        self.keyword = keyword.lower() # Case-insensitive matching

    def filter(self, record: logging.LogRecord) -> bool:
        # Return True if the message should be logged, False otherwise.
        # We want to log if the keyword is NOT in the message.
        return self.keyword not in record.getMessage().lower()


if __name__ == '__main__':
    # --- Create logs directory if it doesn't exist ---
    # This is good practice for the example to run smoothly, especially for first-time execution.
    import os
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)
        print(f"Created directory: {LOGS_DIR}")

    # --- Define Module-Specific File Configurations ---
    # These demonstrate configuring loggers that write to their own dedicated files
    # in addition to the console. They will NOT write to `katana_events.log`.
    module_files_setup = {
        # 'katana_logger.core' will log DEBUG and above to console and core.log
        f"{DEFAULT_LOGGER_NAME}.core": {
            "filename": CORE_LOG_FILE,
            "level": logging.DEBUG,
        },
        # 'katana_logger.trader' will log INFO and above to console and trader.log
        f"{DEFAULT_LOGGER_NAME}.trader": {
            "filename": TRADER_LOG_FILE,
            "level": logging.INFO,
        },
        # 'katana_logger.voice' will log DEBUG and above to console and voice.log
        f"{DEFAULT_LOGGER_NAME}.voice": {
            "filename": VOICE_LOG_FILE,
            "level": logging.DEBUG,
        },
        # Adding bot logger configuration to the example
        f"{DEFAULT_LOGGER_NAME}.bot": {
            "filename": BOT_LOG_FILE,
            "level": logging.INFO,
        }
    }

    # --- Define General Module Levels (for modules WITHOUT dedicated file handlers) ---
    # These modules will use the handlers of their parent logger (typically DEFAULT_LOGGER_NAME,
    # thus logging to console and `katana_events.log`), but with their own specified log levels.
    general_module_levels_setup = {
        # 'katana_logger.module1' will log DEBUG and above to console & katana_events.log
        f"{DEFAULT_LOGGER_NAME}.module1": logging.DEBUG,
        # 'katana_logger.module2' will log WARNING and above to console & katana_events.log
        f"{DEFAULT_LOGGER_NAME}.module2": logging.WARNING,
        # 'external_lib' is not a child of katana_logger. It will propagate to root.
        # Its visibility depends on root logger config (Python default: WARNING+ to stderr).
        "external_lib": logging.INFO
    }

    # --- Setup Logging Configuration ---
    # The main `katana_logger` itself will be set to log at INFO level.
    setup_logging(
        log_level=logging.INFO, # Log level for DEFAULT_LOGGER_NAME
        module_file_configs=module_files_setup,
        module_levels=general_module_levels_setup
    )

    # --- Get Logger Instances ---
    # It's standard practice to obtain logger instances in each module that needs logging.
    main_katana_logger = get_logger() # Gets 'katana_logger'
    core_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.core") # Gets 'katana_logger.core'
    trader_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.trader") # Gets 'katana_logger.trader'
    voice_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.voice") # Gets 'katana_logger.voice'
    bot_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.bot") # Gets 'katana_logger.bot'

    # Loggers for modules that propagate to main_katana_logger
    module1_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.module1")
    module2_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.module2")

    # Logger not explicitly configured; inherits from main_katana_logger as its parent.
    propagating_child_logger = get_logger(f"{DEFAULT_LOGGER_NAME}.propagating_child")

    # Logger for an "external" library.
    external_logger = get_logger("external_lib")

    # --- Log Messages: Demonstrating Different Scenarios ---
    print(f"\n--- Logging examples (check console and log files in ./{LOGS_DIR}/) ---")

    # Scenario 1: Logging from the main Katana logger
    # Expected: INFO level; output to console and logs/katana_events.log
    print("\nTesting main_katana_logger (console, katana_events.log)...")
    main_katana_logger.debug("main_katana_logger: DEBUG (Should NOT be visible; main_katana_logger level is INFO)")
    main_katana_logger.info("main_katana_logger: INFO message.")

    # Scenario 2: Logging from a module with a dedicated file handler ('core')
    # Expected: DEBUG level; output to console and logs/core.log
    print("\nTesting core_logger (console, core.log)...")
    core_logger.debug("core_logger: DEBUG message.")
    core_logger.info("core_logger: INFO message.")

    # Scenario 3: Logging from another module with a dedicated file handler ('trader')
    # Expected: INFO level; output to console and logs/trader.log
    print("\nTesting trader_logger (console, trader.log)...")
    trader_logger.debug("trader_logger: DEBUG message (Should NOT be visible; trader_logger level is INFO)")
    trader_logger.info("trader_logger: INFO message.")

    # Scenario 4: Logging from 'voice' module
    # Expected: DEBUG level; output to console and logs/voice.log
    print("\nTesting voice_logger (console, voice.log)...")
    voice_logger.debug("voice_logger: DEBUG message.")

    # Scenario 4b: Logging from 'bot' module (newly added to example)
    # Expected: INFO level; output to console and logs/bot.log
    print("\nTesting bot_logger (console, bot.log)...")
    bot_logger.debug("bot_logger: DEBUG message (Should NOT be visible; bot_logger level is INFO)")
    bot_logger.info("bot_logger: INFO message.")

    # Scenario 5: Logging from 'module1' (propagates to main_katana_logger)
    # Expected: DEBUG level; output to console and logs/katana_events.log
    print("\nTesting module1_logger (console, katana_events.log via main_katana_logger)...")
    module1_logger.debug("module1_logger: DEBUG message.")
    module1_logger.info("module1_logger: INFO message.") # Also visible as it's >= DEBUG

    # Scenario 6: Logging from 'module2' (propagates to main_katana_logger)
    # Expected: WARNING level; output to console and logs/katana_events.log
    print("\nTesting module2_logger (console, katana_events.log via main_katana_logger)...")
    module2_logger.info("module2_logger: INFO message (Should NOT be visible; module2_logger level is WARNING)")
    module2_logger.warning("module2_logger: WARNING message.")

    # Scenario 7: Logging from an unconfigured child (propagates to main_katana_logger)
    # Expected: Inherits INFO level from main_katana_logger; output to console and logs/katana_events.log
    print("\nTesting propagating_child_logger (console, katana_events.log via main_katana_logger)...")
    propagating_child_logger.debug("propagating_child_logger: DEBUG (Should NOT be visible; inherits INFO)")
    propagating_child_logger.info("propagating_child_logger: INFO message.")

    # Scenario 8: Logging from an external library logger
    # Expected: INFO level (set by module_levels); propagates to root.
    # Output visibility depends on root logger's handlers (Python's default streams WARNING+ to stderr).
    print("\nTesting external_logger (propagates to root, level INFO)...")
    external_logger.debug("external_lib: DEBUG message (Likely not visible unless root handler is DEBUG)")
    external_logger.info("external_lib: INFO message (Likely not visible unless root handler is INFO/DEBUG)")
    external_logger.warning("external_lib: WARNING message (Should be visible on stderr by default).")

    # --- Test Filter on Main Katana Logger's Handlers ---
    # This filter will affect `main_katana_logger` and any loggers that propagate to it
    # (e.g., `module1_logger`, `module2_logger`, `propagating_child_logger`).
    # It will NOT affect loggers with `propagate: False` and their own handlers (e.g., `core_logger`).
    print("\n--- Adding filter to EXCLUDE messages containing 'secret' from main_katana_logger's handlers (console & katana_events.log) ---")
    keyword_filter = KeywordFilter("secret")
    add_filter_to_main_logger(keyword_filter) # Affects console and default_file handlers of main_katana_logger

    # Test main_katana_logger after filter
    main_katana_logger.info("main_katana_logger: INFO message after filter (no secret).")
    main_katana_logger.info("main_katana_logger: This is a SECRET INFO message. (Should be filtered out from console & katana_events.log)")

    # Test a propagating child logger (module1) after filter on main
    module1_logger.info("module1_logger: INFO message with a secret. (Should also be filtered from console & katana_events.log)")

    # Test a logger with its own handlers (core_logger); should NOT be affected by the filter on main_katana_logger.
    core_logger.info("core_logger: INFO message with a secret. (Should NOT be filtered from console or core.log)")
    trader_logger.info("trader_logger: INFO message with a secret. (Should NOT be filtered from console or trader.log)")

    # --- Final Information ---
    print(f"\n--- End of Example ---")
    print(f"Log files have been created/updated in the './{LOGS_DIR}/' directory:")
    print(f"  - Main application events: {DEFAULT_LOG_FILE_NAME}")
    print(f"  - Core module specific logs: {CORE_LOG_FILE}")
    print(f"  - Trader module specific logs: {TRADER_LOG_FILE}")
    print(f"  - Voice module specific logs: {VOICE_LOG_FILE}")
    print(f"  - Bot module specific logs: {BOT_LOG_FILE}") # Added bot log to example output
    print("Please review the console output and the contents of these log files to verify the logging behavior.")
