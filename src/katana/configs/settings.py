import logging
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Centralized application settings.
    Settings are loaded from .env file or environment variables.
    """
    # Telegram Adapter Settings
    telegram_token: str = Field(..., description="The secret token for the Telegram Bot API.")

    # Redis Memory Service Settings
    redis_url: str = Field("redis://localhost:6379/0", description="URL for the Redis instance used for memory.")

    # Logging Settings
    log_level: str = Field("INFO", description="Logging level, e.g., DEBUG, INFO, WARNING, ERROR.")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create a single, reusable instance of the settings
try:
    settings = Settings()
except Exception as e:
    # This provides a more helpful error message if settings fail to load.
    logging.critical(f"Failed to load application settings: {e}")
    # You might want to exit the application here if settings are critical
    exit(1)
