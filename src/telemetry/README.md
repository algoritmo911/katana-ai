# Telemetry Module

This module is responsible for logging application events and traces.

## Logging

The primary logging configuration is defined in `logger_config.py`. It utilizes Python's built-in `logging` module.

Key features:
- **Rotating Logs**: Logs are automatically rotated when they reach a certain size to prevent them from growing indefinitely. The `RotatingFileHandler` is used for this.
- **Log Level**: The default logging level is set to `INFO`. This can be configured in `logger_config.py`.
- **Log Format**: Logs include a timestamp, logger name, log level, and the message.

### How to Use the Logger

To use the logger in any module of your application, import the `get_logger` function from `logger_config.py`:

```python
from src.telemetry.logger_config import get_logger

# Get a logger instance specific to the current module
logger = get_logger(__name__)

# Example usage
logger.info("This is an informational message.")
logger.error("This is an error message.")
logger.warning("This is a warning message.")
logger.debug("This is a debug message (will not appear if level is INFO).")
```

### Using a Decorator for Tracing (Example)

While not implemented by default in `logger_config.py`, you can easily create a decorator to log function calls, arguments, and return values. Here's a conceptual example:

```python
import functools
from src.telemetry.logger_config import get_logger

# Assume logger is configured as above
trace_logger = get_logger("tracer")

def trace_function(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        trace_logger.info(f"Calling function: {func.__name__} with args: {args}, kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            trace_logger.info(f"Function {func.__name__} returned: {result}")
            return result
        except Exception as e:
            trace_logger.error(f"Function {func.__name__} raised an exception: {e}", exc_info=True)
            raise
    return wrapper

# Example of using the decorator
# @trace_function
# def my_function(x, y):
#     return x + y
```
To use such a decorator, you would uncomment it and place `@trace_function` above the function definition you want to trace.

## Log Location and Reading

- **Log Files**: Application logs are stored in the `logs/` directory at the root of the project.
- **Main Log File**: The primary log file is `logs/app.log`.
- **Rotation**: When `app.log` reaches its maximum size (configured in `logger_config.py`), it is renamed to `app.log.1`, and a new `app.log` is created. This process continues with `app.log.2`, etc., up to the configured backup count.

### How to Read Logs

You can read the log files using any text editor or command-line tools like `cat`, `less`, or `tail`.

Example using `tail` to follow the log in real-time:
```bash
tail -f logs/app.log
```

To view older, rotated logs:
```bash
less logs/app.log.1
```

Logs are plain text and formatted for readability. Each line typically represents a single log event.
