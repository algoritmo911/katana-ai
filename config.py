# config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, AnyHttpUrl

# Base directory of the project
BASE_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "logs"

# Create logs directory if it doesn't exist
LOGS_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    """
    Application settings, loaded from .env file and environment variables.
    Utilizes Pydantic for validation and type safety.
    """
    # .env file is loaded automatically by pydantic-settings
    model_config = SettingsConfigDict(
        env_file=f"{BASE_DIR}/.env",
        env_file_encoding='utf-8',
        case_sensitive=False
    )

    # Telegram Bot Settings
    # The token is a secret, so we use SecretStr to prevent it from being shown in logs
    telegram_bot_token: SecretStr

    # Webhook settings (will be used by the FastAPI server)
    # Example: https://your-domain.com
    webhook_host: AnyHttpUrl = "http://localhost:8000"
    # The path to which Telegram will send updates
    # e.g., /telegram/webhook
    webhook_path: str = "/webhook"

    @property
    def webhook_url(self) -> str:
        """Constructs the full webhook URL."""
        # get_secret_value() is used to access the actual token string
        return f"{self.webhook_host}{self.webhook_path}"

    # Logging configuration
    log_level: str = "INFO"
    log_file_main: Path = LOGS_DIR / "main.log"
    log_file_errors: Path = LOGS_DIR / "errors.log"


# Instantiate the settings
settings = Settings()

# You can now import 'settings' from this module to access configuration
# e.g., from config import settings
# settings.telegram_bot_token.get_secret_value()

if __name__ == '__main__':
    # This block is for testing the configuration loading
    print("--- Configuration Loaded ---")
    # Use .get_secret_value() to reveal the token for debugging purposes
    print(f"Telegram Bot Token: {settings.telegram_bot_token.get_secret_value()[:8]}... (hidden)")
    print(f"Webhook Host: {settings.webhook_host}")
    print(f"Webhook Path: {settings.webhook_path}")
    print(f"Full Webhook URL: {settings.webhook_url}")
    print(f"Log Level: {settings.log_level}")
    print(f"Main Log File: {settings.log_file_main}")
    print(f"Errors Log File: {settings.log_file_errors}")
    print("--------------------------")

    if "YOUR_TELEGRAM_BOT_TOKEN_HERE" in settings.telegram_bot_token.get_secret_value():
        print("\nWarning: It seems you are using the default placeholder for TELEGRAM_BOT_TOKEN.")
        print("Please create a .env file in the root directory with your actual token:")
        print(f"Example .env file content:\nTELEGRAM_BOT_TOKEN=\"123456:ABC-DEF1234ghIkl-zyx57W2v1uT0\"")
