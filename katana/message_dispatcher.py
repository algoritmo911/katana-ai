import logging
from katana.routing.agent_router import AgentRouter

logger = logging.getLogger(__name__)

class MessageDispatcher:
    def __init__(self):
        self.router = AgentRouter()

    async def dispatch(self, source, user_id, message):
        logger.info(f"Dispatching message from {source} for user {user_id}")
        bot = self.router.get_bot(user_id)

        # This is a temporary solution. The bot's handle_message method should be async.
        # For now, we'll run it in a separate thread to avoid blocking the event loop.
        # In a real implementation, we would use a proper task queue.
        import asyncio
        loop = asyncio.get_event_loop()

        # The logic to select the bot type will be added later.
        # For now, we'll use the default bot's handle_command method.
        if hasattr(bot, 'handle_command'):
            response = await loop.run_in_executor(None, bot.handle_command, message)
        elif hasattr(bot, 'handle_message'):
            response = await loop.run_in_executor(None, bot.handle_message, message)
        else:
            response = "Bot has no message handler."

        self.router.release_bot(user_id)
        return response
