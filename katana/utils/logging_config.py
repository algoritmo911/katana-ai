import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone
import sys
import os # Added for environment variable access

try:
    import colorlog # Added for colored logging
except ImportError:
    colorlog = None


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        standard_attrs = [
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
        ]
        # Add any extra fields passed to the logger
        for key, value in record.__dict__.items():
            if key not in standard_attrs and key not in log_record:
                log_record[key] = value

        return json.dumps(log_record)


class ColoredFormatter(logging.Formatter):
    """
    A logging formatter that uses colorlog if available, otherwise falls back to a standard formatter.
    """
    def __init__(self, fmt: str, datefmt: str = None, style: str = '%', use_colors: bool = True):
        super().__init__() # Basic initialization
        if colorlog and use_colors:
            self.formatter = colorlog.ColoredFormatter(
                fmt='%(log_color)s' + fmt,
                datefmt=datefmt,
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                },
                secondary_log_colors={},
                style=style
            )
        else:
            self.formatter = logging.Formatter(fmt, datefmt=datefmt, style=style)

    def format(self, record: logging.LogRecord) -> str:
        # Temporarily store original message if it's already formatted (e.g. by JsonFormatter for file)
        # This is a bit of a workaround if a record is processed by multiple formatters.
        # Usually, a handler has one formatter.
        return self.formatter.format(record)


def setup_logger(
    logger_name: str,
    log_file_path_str: str, # This will be "command_telemetry.log" as per requirements
    level: int = logging.DEBUG,
    max_bytes: int = 1024 * 1024,  # 1MB
    backup_count: int = 5,
    dev_mode: bool = False, # Added dev_mode flag
):
    """
    Configures and returns a logger with JSON file logging and optional colored console logging.
    File logging is always JSON. Console logging is colored if dev_mode is True and colorlog is available.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Remove any existing handlers to prevent duplication
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    logger.propagate = False

    # File Handler (JSON) - always active
    # The requirement is for "command_telemetry.log"
    # We assume log_file_path_str will be passed as "command_telemetry.log" by the caller.
    log_file_path = Path(log_file_path_str)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file_path_str, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    # Console Handler (Colored or Standard based on dev_mode and colorlog availability)
    # As per requirement: "вывод в консоль в dev" (console output in dev)
    is_dev_env = os.environ.get("ENV_MODE", "").lower() == "dev" or dev_mode

    if is_dev_env:
        console_handler = logging.StreamHandler(sys.stdout)
        console_format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(message)s (%(module)s.%(funcName)s:%(lineno)d)"
        )

        # Use ColoredFormatter if colorlog is available, otherwise standard
        if colorlog:
            console_formatter = ColoredFormatter(
                fmt=console_format_string,
                datefmt="%Y-%m-%d %H:%M:%S",
                use_colors=True
            )
        else: # Fallback if colorlog is not installed
            console_formatter = logging.Formatter(console_format_string, datefmt="%Y-%m-%d %H:%M:%S")
            if not colorlog: # Add a message if colorlog is missing but was expected
                 logger.info("colorlog module not found, console output will not be colored.")


        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    return logger
