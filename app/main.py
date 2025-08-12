import asyncio
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from fastapi import FastAPI
from loguru import logger

from config import settings

# Configure Loguru
# ------------------------------------------------------------------------------
# Define a log format that includes the trace_id from the context
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<yellow>TraceID: {extra[trace_id]}</yellow> | "
    "<level>{message}</level>"
)

logger.remove()
# Console logger with the custom format
logger.add(sys.stderr, level=settings.log_level, format=LOG_FORMAT)
# File loggers
logger.add(settings.log_file_main, level=settings.log_level, rotation="10 MB", compression="zip", enqueue=True, format=LOG_FORMAT)
logger.add(settings.log_file_errors, level="ERROR", rotation="10 MB", compression="zip", enqueue=True, format=LOG_FORMAT)
# ------------------------------------------------------------------------------

# Import middlewares
from app.middlewares.logging import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for FastAPI's lifespan.
    It runs startup and shutdown logic for the application.
    """
    logger.info("Application startup...")

    # Register middlewares
    # The logging middleware should be the first one to catch the request early
    app.state.dp.update.middleware(LoggingMiddleware())

    # Register handlers
    from app.handlers import common, message
    logger.info("Registering handlers...")
    app.state.dp.include_router(common.router)
    app.state.dp.include_router(message.router)
    logger.info("Handlers registered successfully.")

    logger.info(f"Setting up webhook to: {settings.webhook_url}")
    bot = app.state.bot
    await bot.set_webhook(
        url=settings.webhook_url,
        allowed_updates=app.state.dp.resolve_used_update_types(),
        secret_token=settings.telegram_bot_token.get_secret_value() # Recommended for security
    )
    logger.info("Webhook has been set.")

    yield

    logger.info("Application shutdown...")
    await app.state.bot.delete_webhook()
    logger.info("Webhook has been deleted.")
    await app.state.dp.storage.close()
    logger.info("Dispatcher storage closed.")


# Initialize FastAPI app with the lifespan context manager
app = FastAPI(lifespan=lifespan)

# Initialize Aiogram Bot and Dispatcher
# We use app.state to store the bot and dispatcher instances, making them accessible
# within FastAPI's request scope (e.g., in path operation functions).
bot = Bot(token=settings.telegram_bot_token.get_secret_value(), parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Store bot and dispatcher instances in app.state
app.state.bot = bot
app.state.dp = dp

@app.get("/")
async def root():
    """
    Root endpoint for health checks.
    """
    return {"status": "ok", "project": "Katana-AI", "stage": "Simbiont"}

@app.post(settings.webhook_path)
async def telegram_webhook(update: dict):
    """
    This endpoint will receive updates from Telegram.
    The update is a raw dictionary, which is then fed into the aiogram dispatcher.
    """
    # The dispatcher will process the update and call the appropriate handlers
    await dp.feed_webhook_update(bot, update)

    return {"status": "ok"}

# --- Management Endpoints ---
# These endpoints are for manually managing the webhook, useful for development/debugging.

@app.get("/management/set-webhook")
async def set_webhook_endpoint():
    """
    Manually sets the webhook for the bot.
    """
    logger.info("Attempting to manually set webhook...")
    try:
        await bot.set_webhook(
            url=settings.webhook_url,
            allowed_updates=dp.resolve_used_update_types(),
            secret_token=settings.telegram_bot_token.get_secret_value()
        )
        logger.info(f"Webhook set successfully to: {settings.webhook_url}")
        return {"status": "success", "message": "Webhook has been set."}
    except Exception as e:
        logger.exception("Failed to set webhook")
        return {"status": "error", "message": str(e)}

@app.get("/management/delete-webhook")
async def delete_webhook_endpoint():
    """
    Manually deletes the webhook for the bot.
    """
    logger.info("Attempting to manually delete webhook...")
    try:
        await bot.delete_webhook()
        logger.info("Webhook deleted successfully.")
        return {"status": "success", "message": "Webhook has been deleted."}
    except Exception as e:
        logger.exception("Failed to delete webhook")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    # This block allows running the app directly for development/testing.
    # In production, you would use a process manager like Gunicorn with Uvicorn workers.
    logger.info("Starting Uvicorn server for development...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
