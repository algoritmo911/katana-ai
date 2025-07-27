import logging
from katana.message_dispatcher import MessageDispatcher

logger = logging.getLogger(__name__)

class ApiInterface:
    def __init__(self, dispatcher: MessageDispatcher):
        self.dispatcher = dispatcher

    async def handle_message(self, user_id, message):
        logger.info(f"Handling API message from user {user_id}")
        response = await self.dispatcher.dispatch("api", user_id, message)
        return response
