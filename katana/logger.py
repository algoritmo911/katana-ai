from .core.logging.standard_logger import setup_logging, get_logger, log_command_trace
import os

# Read environment variables
LOG_LEVEL = os.environ.get("KATANA_LOG_LEVEL", "INFO").upper()
LOG_TO_FILE = os.environ.get("KATANA_LOG_TO_FILE", "false").lower() == "true"
LOG_FILE_PATH = os.environ.get("KATANA_LOG_FILE_PATH", "logs/katana.log")

# Setup logging
setup_logging(log_level=LOG_LEVEL, log_to_file=LOG_TO_FILE, log_file_path=LOG_FILE_PATH)
