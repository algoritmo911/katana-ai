import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone
import sys
import os # Added for environment variable access

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

    # Console Handler (Standard based on dev_mode)
    # As per requirement: "вывод в консоль в dev" (console output in dev)
    is_dev_env = os.environ.get("ENV_MODE", "").lower() == "dev" or dev_mode

    if is_dev_env:
        console_handler = logging.StreamHandler(sys.stdout)
        console_format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(message)s (%(module)s.%(funcName)s:%(lineno)d)"
        )

        # Standard formatter
        console_formatter = logging.Formatter(console_format_string, datefmt="%Y-%m-%d %H:%M:%S")

        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    return logger
