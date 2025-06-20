# Katana Logging System (`katana_logger.py`)

This document describes the centralized logging system used within the Katana project, provided by the `katana_logger.py` module.

## Overview

The `katana_logger` module offers a standardized way to implement logging across different components of the Katana application. It utilizes Python's built-in `logging` library and provides a simple interface to obtain pre-configured logger instances.

## Features

-   **Standardized Log Format**: All log messages adhere to a uniform format for consistency and easier parsing.
    -   Format: `[TIMESTAMP] [MODULE_NAME] [USER_ID] [LEVEL]: MESSAGE`
    -   Example: `[2023-10-27T10:30:00.123Z] [katana.bot.katana_bot] [user12345] [INFO]: Received /start command`
-   **Configurable Log Levels**: Supports standard logging levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
-   **Dynamic Log Level Configuration**: The log level for all Katana loggers can be set globally via the `KATANA_LOG_LEVEL` environment variable.
-   **User ID Tracking**: Includes a `USER_ID` field in log metadata to help trace actions associated with specific users or system processes.
-   **Easy Integration**: Simple function call to get a logger instance for any module.

## How to Use

To use the logger in your Python module within the Katana project:

1.  **Import the `get_logger` function:**

    ```python
    from katana.utils.katana_logger import get_logger
    ```

2.  **Get a logger instance:**

    It's recommended to get a logger instance at the module level, using the module's `__name__`.

    ```python
    logger = get_logger(__name__)
    ```

    You can also specify a default `user_id` for all messages logged by this logger instance if a more specific `user_id` is not provided at the time of logging:

    ```python
    logger = get_logger(__name__, user_id="my_default_user_or_service_id")
    ```
    If no `user_id` is specified for `get_logger`, it defaults to "SYSTEM".

3.  **Log messages:**

    Use the standard methods of the logger object (`debug`, `info`, `warning`, `error`, `critical`):

    ```python
    logger.info("This is an informational message.")
    logger.warning("This is a warning message.")
    logger.error("An error occurred.")
    ```

4.  **Logging with User ID:**

    To associate a log message with a specific user ID (which will override any default `user_id` set with `get_logger` for that specific message), use the `extra` parameter:

    ```python
    user_id_variable = "some_user_123"
    logger.info("User-specific action details.", extra={'user_id': user_id_variable})
    ```
    If `extra={'user_id': ...}` is not provided, the `user_id` specified in `get_logger(..., user_id="your_default")` will be used. If that was also not provided, "SYSTEM" will be used.

5.  **Logging Exceptions:**

    To include exception information (traceback) in your error logs, use the `exc_info=True` argument:

    ```python
    try:
        # ... some operation that might fail ...
        risky_operation()
    except Exception as e:
        logger.error("An operation failed.", exc_info=True)
        # Or, to include the exception message directly:
        # logger.error(f"An operation failed: {e}", exc_info=True)
    ```

## Log Levels

-   **DEBUG**: Detailed information, typically of interest only when diagnosing problems.
-   **INFO**: Confirmation that things are working as expected.
-   **WARNING**: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., ‘disk space low’). The software is still working as expected.
-   **ERROR**: Due to a more serious problem, the software has not been able to perform some function.
-   **CRITICAL**: A serious error, indicating that the program itself may be unable to continue running.

## Configuration

### Setting Log Level via Environment Variable

The default log level is `INFO`. You can change the log level for all loggers obtained through `get_logger` by setting the `KATANA_LOG_LEVEL` environment variable.

For example, to set the log level to `DEBUG`:

```bash
export KATANA_LOG_LEVEL=DEBUG
```

Supported values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (case-insensitive).

## Log Output

Currently, all logs are written to `stdout` (console).

## Future Enhancements (Potential)

-   Output to files.
-   Integration with external logging services.
-   More granular configuration options (e.g., per-module log levels via a config file).
