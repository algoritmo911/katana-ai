import logging
import json

logger = logging.getLogger(__name__)

class BaseBot:
    def __init__(self, bot_name="BaseBot", profile=None):
        self.name = bot_name
        self.profile = profile or {}
        self.memory = {}  # For storing conversation history, etc.

    def load_profile(self, profile_path):
        with open(profile_path, 'r') as f:
            self.profile = json.load(f)
        self.name = self.profile.get("name", self.name)
        logger.info(f"Bot {self.name} loaded profile from {profile_path}")

    def clone(self, new_bot_name):
        new_bot = self.__class__(bot_name=new_bot_name, profile=self.profile.copy())
        logger.info(f"Cloned bot {self.name} to {new_bot_name}")
        return new_bot

    def handle_message(self, message):
        raise NotImplementedError("Each bot must implement its own message handler.")

    def get_status(self):
        return "available"  # Simple status for now
