# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
KATANA_API_ENDPOINT = os.getenv("KATANA_API_ENDPOINT", "http://localhost:8000/api") # Example API endpoint

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE_TELEGRAM = "logs/telegram.log"
LOG_FILE_KATANA = "logs/katana.log"
LOG_FILE_NLP = "logs/nlp.log"

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("Warning: TELEGRAM_BOT_TOKEN is not set. Please set it in .env file or environment variables.")

if __name__ == '__main__':
    print(f"Telegram Bot Token: {TELEGRAM_BOT_TOKEN}")
    print(f"Katana API Endpoint: {KATANA_API_ENDPOINT}")
    print(f"Log Level: {LOG_LEVEL}")
    print(f"Telegram Log File: {LOG_FILE_TELEGRAM}")
