# katana-ai

## Logging System

The Katana application uses a centralized and configurable logging system based on Python's `logging` module. It's configured via `katana/logging_config.py`.

### Overview
- **Main Logger:** The primary logger is named `katana_logger`. This is the root for most application-specific logging.
- **Configuration:** Logging is set up using the `setup_logging()` function in `katana.logging_config`. This function utilizes `logging.config.dictConfig` for a flexible, dictionary-based configuration.
- **Console Output:** By default, most configured loggers also output to the console (stderr), allowing for real-time monitoring.

### Logger Hierarchy
- **`katana_logger`**: This is the main application logger.
- **Module-Specific Loggers**: Different parts of the application use child loggers of `katana_logger`. Common examples include:
    - `katana_logger.core`
    - `katana_logger.mci_agent` (often logs under `katana_logger.core`)
    - `katana_logger.trader`
    - `katana_logger.voice`
    - `katana_logger.bot` (may log under `katana_logger.voice` or its own category)
- Loggers are hierarchical. For example, `katana_logger.core.some_sub_module` is a child of `katana_logger.core`.

### Adding Logging to a New Module
To add logging to your Python module:
1. Import the `get_logger` function:
   ```python
   from katana.logging_config import get_logger
   ```
2. Obtain a logger instance at the top of your module:
   ```python
   # Preferred method for modules within the 'katana' package structure:
   logger = get_logger(__name__)
   # This will create a logger named, e.g., 'katana.your_module.submodule'.
   # Ensure this name or its parent (e.g., 'katana.your_module' or 'katana_logger')
   # is configured in logging_config.py if specific handling is needed.

   # Alternatively, for a specific feature area aligned with top-level loggers:
   # logger = get_logger('katana_logger.core.my_new_component')
   ```
   Using `__name__` is generally recommended as it naturally follows your package structure. The logging configuration can then control behavior based on these hierarchical names.

3. Use the logger instance to log messages:
   ```python
   logger.info("This is an informational message.")
   logger.debug("This is a debug message for development.")
   logger.warning("Something unexpected but not critical happened.")
   logger.error("An error occurred!", exc_info=True) # exc_info=True logs the current exception stack trace
   logger.critical("A critical error occurred, application might be unstable.")
   ```

### Configuration (`katana.logging_config.setup_logging`)
The core of the logging setup is the `setup_logging` function in `katana.logging_config.py`. It allows for detailed control over log levels, handlers, and formatting.

- **Customizing Log Levels**:
    - **`log_level` (int parameter for `setup_logging`):** Sets the default level for the main `katana_logger` (e.g., `logging.INFO`).
    - **`module_levels` (Dict[str, int] parameter):** Allows setting specific log levels for any logger by its name. For example:
      ```python
      # To set 'katana_logger.trader' to DEBUG level:
      setup_logging(module_levels={"katana_logger.trader": logging.DEBUG})
      ```
      Loggers configured this way (without dedicated files via `module_file_configs`) typically propagate messages to their parent's handlers.

- **Module-Specific Log Files**:
    - The `module_file_configs` parameter in `setup_logging` is used to define dedicated log files for specific modules. These use `RotatingFileHandler` for log rotation.
      ```python
      module_files_config = {
          "katana_logger.core": {  # Logger name
              "filename": "logs/core.log",  # Dedicated file
              "level": logging.DEBUG,        # Log level for this logger
              # "maxBytes": ...,             # Optional: Override default MAX_BYTES
              # "backupCount": ...,          # Optional: Override default BACKUP_COUNT
          },
          "katana_logger.trader": {
              "filename": "logs/trader.log",
              "level": logging.INFO,
          }
          # Add other modules as needed
      }
      setup_logging(module_file_configs=module_files_config)
      ```

- **`propagate = False` for Loggers with Dedicated Files**:
    - When a logger (e.g., `katana_logger.core`) is configured with its own dedicated file handler via `module_file_configs`, the setup automatically sets `propagate = False` for that logger.
    - **Significance**: This means that log messages sent to `katana_logger.core` will go to:
        1. Its dedicated file handler (e.g., `logs/core.log`).
        2. The shared 'console' handler.
    - Crucially, these messages will *not* be passed up to the handlers of the parent logger (`katana_logger`). This prevents the same log message from appearing in both `logs/core.log` and `logs/katana_events.log`, avoiding duplication.
    - Child loggers of `katana_logger.core` (e.g., `katana_logger.core.submodule`) will still propagate their messages to `katana_logger.core`'s handlers by default, unless they too are configured with `propagate = False`.

### Filtering Logs
- The logging system supports filtering. A `KeywordFilter` example is provided in `katana.logging_config.py`.
- The function `add_filter_to_main_logger(filter_instance)` can be used to add a filter to the handlers of `katana_logger` (i.e., the console output and `logs/katana_events.log`).
- Filters for module-specific dedicated log files (e.g., `core.log`) are not currently managed by this specific function. If needed, filters would have to be added directly to their respective handlers during the `dictConfig` setup or via a more generic filter utility.

### Log File Locations and Purpose
The primary log files are stored in the `logs/` directory:

- **`logs/katana_events.log`**:
    - **Purpose**: Captures general application-wide logs from `katana_logger` and any child modules that propagate to it. This file is useful for getting an overview of application activity and for logs from modules that don't have a dedicated log file.
    - **Logged by**: `katana_logger` and its children (e.g., `katana_logger.module1`, `katana_logger.some_utility`) that *do not* have `propagate = False` set through a `module_file_configs` entry.

- **`logs/core.log`**:
    - **Purpose**: Dedicated logs for core system functionalities, including the `katana_core` agent and potentially `mci_agent` operations if configured under `katana_logger.core`.
    - **Logged by**: `katana_logger.core` and its children (e.g., `katana_logger.core.sub_component`).

- **`logs/trader.log`**:
    - **Purpose**: Specific to trading logic, operations, API interactions, and financial transactions.
    - **Logged by**: `katana_logger.trader` and its children.

- **`logs/voice.log`**:
    - **Purpose**: Logs related to voice input/output, speech recognition, text-to-speech, and potentially general bot interaction logic if not separated further.
    - **Logged by**: `katana_logger.voice` (and potentially `katana_logger.bot` or its children, depending on final logger naming for bot functionalities).

It is recommended to consult `katana/logging_config.py` for the most up-to-date details on the `dictConfig` structure and available configuration options.