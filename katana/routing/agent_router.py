import logging
import uuid
from katana.bots.default_bot import KatanaBot

logger = logging.getLogger(__name__)

class AgentRouter:
    def __init__(self):
        self.bots = {}
        self.user_to_bot = {}

    def get_bot(self, user_id):
        if user_id in self.user_to_bot:
            bot_id = self.user_to_bot[user_id]
            if self.bots[bot_id]['status'] == 'available':
                return self.bots[bot_id]['instance']

        for bot_id, bot_info in self.bots.items():
            if bot_info['status'] == 'available':
                self.user_to_bot[user_id] = bot_id
                return bot_info['instance']

        new_bot_id = str(uuid.uuid4())
        new_bot = KatanaBot(bot_name=f"KatanaBot-{new_bot_id}")
        self.bots[new_bot_id] = {'instance': new_bot, 'status': 'available'}
        self.user_to_bot[user_id] = new_bot_id
        logger.info(f"Created new bot {new_bot_id} for user {user_id}")
        return new_bot

    def release_bot(self, user_id):
        if user_id in self.user_to_bot:
            bot_id = self.user_to_bot.pop(user_id)
            # In a more complex scenario, you might not immediately make the bot available
            # but for now, we will.
            if bot_id in self.bots:
                self.bots[bot_id]['status'] = 'available'
                logger.info(f"Bot {bot_id} released by user {user_id}")
