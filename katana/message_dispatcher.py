import logging
import json
from katana.routing.agent_router import AgentRouter

logger = logging.getLogger(__name__)


class MessageDispatcher:
    def __init__(self):
        self.router = AgentRouter()

    async def dispatch(self, source, user_id, message):
        logger.info(f"Dispatching message from {source} for user {user_id}")

        try:
            task = json.loads(message)
            if not isinstance(task, dict):
                raise ValueError("Message is not a JSON object.")
        except (json.JSONDecodeError, ValueError):
            # Message is not a valid JSON task, treat it as a simple command.
            bot = self.router.get_bot(user_id) # Get default bot
            if hasattr(bot, 'handle_command'):
                response = bot.handle_command(message)
            elif hasattr(bot, 'handle_message'):
                response = bot.handle_message(message)
            else:
                response = "Bot has no message handler."
            return response

        # We have a valid task object, let's route it.
        bot = self.router.route_task(task)

        # This is a temporary solution. The bot's handle_task method should be async.
        # For now, we'll run it in a separate thread to avoid blocking the event loop.
        # In a real implementation, we would use a proper task queue.
        import asyncio
        loop = asyncio.get_event_loop()

        if hasattr(bot, 'handle_task'):
            response = await loop.run_in_executor(None, bot.handle_task, task)
        else:
            logger.warning(f"Bot {bot.name} has no handle_task method. Falling back to handle_message.")
            response = await loop.run_in_executor(None, bot.handle_message, task.get('content', ''))

        return response
