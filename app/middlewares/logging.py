import uuid
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging and request tracing.
    It generates a unique trace_id for each incoming update and binds it
    to the logger's context, ensuring all log records for a specific
    update share the same identifier.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Generate a unique ID for tracing this specific request
        trace_id = str(uuid.uuid4())

        # Contextualize the logger to include the trace_id in all subsequent logs
        with logger.contextualize(trace_id=trace_id):
            logger.info("Received new update", update_type=event.__class__.__name__)
            try:
                # Proceed with handling the event
                return await handler(event, data)
            except Exception as e:
                # Log any exception that occurs during handling
                logger.exception("An error occurred during event handling")
                # Re-raise the exception to be handled by higher-level error handlers if any
                raise
            finally:
                logger.info("Finished processing update")
