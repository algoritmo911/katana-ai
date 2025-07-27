# Katana Logging

The Katana project uses a centralized logging system to provide standardized and extensible logging throughout the application.

## Configuration

The logging system is configured in the `katana/logger.py` module. The following environment variables can be used to configure the logger:

- `KATANA_LOG_LEVEL`: The log level to use. Can be `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. Defaults to `INFO`.
- `KATANA_LOG_TO_FILE`: Whether to log to a file. Can be `true` or `false`. Defaults to `false`.
- `KATANA_LOG_FILE_PATH`: The path to the log file. Defaults to `logs/katana.log`.

## Usage

To use the logger in your code, you need to import the `get_logger` function from the `katana.logger` module and get a logger instance:

```python
from katana.logger import get_logger

logger = get_logger(__name__)

logger.info("This is an info message.")
logger.warning("This is a warning message.")
```

### Command Tracing

The logger also provides a decorator to trace the execution of command functions. To use it, you need to import the `log_command_trace` decorator from the `katana.logger` module and apply it to your command functions:

```python
from katana.logger import get_logger, log_command_trace

logger = get_logger(__name__)

@log_command_trace(logger)
def my_command(arg1, arg2):
    # ...
```

The decorator will log the entry and exit of the function, including the arguments and the result.
