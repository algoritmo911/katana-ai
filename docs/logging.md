# Standardized Logging

This document describes the standardized logging system used in the Katana project.

## Overview

The logging system is built on top of Python's standard `logging` module and is configured by the `get_logger` function in `src/utils/standard_logger.py`.

The `get_logger` function creates a logger that can be configured to log to both the console and a file. The logging level and file path can be configured using environment variables.

## Configuration

The logger is configured using the following environment variables:

- `LOG_LEVEL`: The logging level. Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. The default is `INFO`.
- `LOG_FILE_PATH`: The path to the log file. If this variable is not set, the logger will only log to the console.

## Usage

To use the logger in a Python script, import the `get_logger` function and call it with the name of the logger:

```python
from src.utils.standard_logger import get_logger

logger = get_logger(__name__)

logger.info("This is an info message.")
logger.warning("This is a warning message.")
```

## Log Rotation

The logger uses a `RotatingFileHandler` to prevent log files from growing indefinitely. The log file is rotated when it reaches 10MB, and up to 5 old log files are kept.
