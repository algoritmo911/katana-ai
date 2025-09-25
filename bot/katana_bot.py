import json
import os
from datetime import datetime, timezone
import random
import telebot

from bot.nlp.parser import Parser
from bot.nlp.nlp_processor import NLPProcessor
from bot.nlp.context import DialogueContextManager

class KatanaBot:
    """
    The core logic unit for the Katana bot.
    Manages conversation state and orchestrates the NLP pipeline.
    Version 2.1: Cleaned up for clarity and robustness.
    """
    def __init__(self, use_telebot=False):
        self.nlp_processor = NLPProcessor()
        self.parser = Parser(self.nlp_processor)
        self.context_manager = DialogueContextManager()
        self.sessions: dict = {}
        self._initialize_intent_handlers()

        self.telebot = None
        if use_telebot:
            self._initialize_telebot()

    def _initialize_intent_handlers(self):
        """Initializes and registers intent handlers."""
        self.intent_handlers = {
            "get_weather": self.handle_get_weather, "tell_joke": self.handle_tell_joke,
            "get_fact": self.handle_get_fact, "greeting": self.handle_greeting,
            "goodbye": self.handle_goodbye, "get_time": self.handle_get_time,
            "fallback_general": self.handle_fallback,
        }

    def _initialize_telebot(self):
        """Initializes the Telebot instance and its handlers."""
        api_token = os.getenv('KATANA_TELEGRAM_TOKEN')
        if not api_token:
            raise ValueError("Telegram API token not found in environment variables.")
        self.telebot = telebot.TeleBot(api_token)
        self._register_telebot_handlers()

    def _register_telebot_handlers(self):
        """Registers message handlers for Telebot."""
        @self.telebot.message_handler(commands=['start', 'help'])
        def telebot_start_handler(message):
            reply = "Hello! I am Katana, your intelligent assistant."
            self.telebot.reply_to(message, reply)

        @self.telebot.message_handler(func=lambda message: True)
        def telebot_message_handler(message):
            response = self.process_chat_message(message.chat.id, message.text)
            if response and response.get("reply"):
                self.telebot.reply_to(message, response["reply"])

    def _get_or_create_session(self, session_id: str) -> dict:
        """Retrieves or creates a new session for a given ID."""
        if session_id not in self.sessions:
            self.log_event(f"Creating new session for ID: {session_id}")
            self.sessions[session_id] = self.context_manager.get_initial_session()
        return self.sessions[session_id]

    def process_chat_message(self, session_id: str, user_text: str) -> dict:
        """
        Processes a user's text message and returns a response.
        This is the primary entry point for the bot's logic.
        """
        self.log_event(f"Processing message from {session_id}: '{user_text}'")

        # 1. Get the current session state
        session = self._get_or_create_session(session_id)

        # 2. Perform NLP analysis on the user's text, using previous history
        # A copy of the history is passed to prevent mutation issues in tests
        nlp_result = self.parser.analyze_text(user_text, history=list(session['history']))
        self.log_event(f"NLP Result for {session_id}: {json.dumps(nlp_result, indent=2)}")

        # 3. Update the conversation context with the new NLP result
        updated_context = self.context_manager.update_context(
            current_context=session["context"],
            nlp_result=nlp_result
        )

        # 4. Determine the intent and generate a response
        intent_name = nlp_result["intents"][0]["name"]
        handler = self.intent_handlers.get(intent_name, self.handle_fallback)
        bot_reply = handler(session_id, updated_context["entities"], updated_context)

        # 5. Update the session with the new context and history entry
        session["context"] = updated_context
        session["history"].append({"user": user_text, "bot": bot_reply})

        # 6. Prepare the final response object for the API
        response_payload = {
            "reply": bot_reply,
            "intent_object": {
                "intent": intent_name,
                "entities": updated_context["entities"],
                "dialogue_state": nlp_result.get("metadata", {}).get("raw_openai_response", {}).get("dialogue_state", "unknown")
            }
        }

        self.log_event(f"Generated response for {session_id}: {bot_reply}")
        return response_payload

    def run_polling(self):
        """Starts the bot in Telegram polling mode."""
        if not self.telebot:
            raise Exception("Telebot not initialized. Instantiate KatanaBot with use_telebot=True.")
        self.log_event("Bot starting in Telegram polling mode...")
        self.telebot.infinity_polling()

    # --- Intent Handlers ---
    def handle_get_weather(self, sid, entities, ctx):
        city = entities.get("city")
        return f"The weather in {city} is great!" if city else "Which city's weather are you asking about?"
    def handle_tell_joke(self, sid, entities, ctx):
        return "Why don't scientists trust atoms? Because they make up everything!"
    def handle_get_fact(self, sid, entities, ctx):
        return "The heart of a shrimp is located in its head."
    def handle_greeting(self, sid, entities, ctx):
        return "Hello there!"
    def handle_goodbye(self, sid, entities, ctx):
        return "Goodbye!"
    def handle_get_time(self, sid, entities, ctx):
        return f"The current time is {datetime.now().strftime('%H:%M:%S')}."
    def handle_fallback(self, sid, entities, ctx):
        return "I'm not sure how to respond to that. Can you try rephrasing?"

    @staticmethod
    def log_event(message: str):
        print(f"[BOT EVENT] {datetime.now(timezone.utc).isoformat()}: {message}")

if __name__ == '__main__':
    bot = KatanaBot(use_telebot=True)
    bot.run_polling()
