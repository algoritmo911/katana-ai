import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
log_file = 'logs/app.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=5), # 5 MB per file, 5 backup files
        logging.StreamHandler() # Also log to console
    ]
)

def get_logger(name):
    return logging.getLogger(name)
