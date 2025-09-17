import telebot
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import random

from bot.nlp.parser import Parser
from bot.nlp.nlp_processor import NLPProcessor
from bot.nlp.context import DialogueContextManager

class KatanaBot:
    """
    Основной класс бота, инкапсулирующий состояние и логику.
    Версия 2.0: Логика обработки отделена от логики Telegram.
    """
    def __init__(self, use_telebot=False):
        self.nlp_processor = NLPProcessor()
        self.parser = Parser(self.nlp_processor)
        self.context_manager = DialogueContextManager()
        self.sessions = {}
        self._initialize_intent_handlers()

        if use_telebot:
            self.api_token = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
            if not self.api_token or ':' not in self.api_token:
                raise ValueError("❌ Invalid or missing Telegram API token.")
            self.telebot = telebot.TeleBot(self.api_token)
            self._register_telebot_handlers()
        else:
            self.telebot = None

    def _initialize_intent_handlers(self):
        self.intent_handlers = {
            "get_weather": self.handle_intent_get_weather, "tell_joke": self.handle_intent_tell_joke,
            "get_fact": self.handle_intent_get_fact, "greeting": self.handle_intent_greeting,
            "goodbye": self.handle_intent_goodbye, "get_time": self.handle_intent_get_time,
            "clarify_city_for_weather": self.handle_intent_clarify_city_for_weather,
            "fallback_general": self.handle_intent_fallback_general,
        }

    def _register_telebot_handlers(self):
        @self.telebot.message_handler(commands=['start', 'help'])
        def handle_start_help(message):
            self.start_command_handler(message)

        @self.telebot.message_handler(func=lambda message: message.content_type == 'text')
        def handle_user_chat_message_telebot(message):
            response = self.process_chat_message(message.chat.id, message.text)
            if response and response.get("reply"):
                self.telebot.reply_to(message, response["reply"])

    def log_event(self, message_text):
        # Исправлено на timezone-aware datetime
        print(f"[BOT EVENT] {datetime.now(timezone.utc).isoformat()}: {message_text}")

    # --- Pipeline Stages ---

    def _prepare_session(self, chat_id):
        if chat_id not in self.sessions:
            self.sessions[chat_id] = self.context_manager.get_initial_session()
        return self.sessions[chat_id]

    def _perform_nlp_analysis(self, text, session):
        # Pass a copy of the history to prevent mutation issues in tests
        return self.parser.analyze_text(text, history=list(session['history']))

    def _generate_response(self, chat_id, intent_name, merged_entities, context):
        handler = self.intent_handlers.get(intent_name, self.handle_intent_fallback_general)
        response_text = handler(chat_id, merged_entities, context)
        return response_text, [{"name": intent_name, "processed": True, "response": response_text}]

    def _update_history(self, session, user_text, bot_response):
        session["history"].append({"user": user_text, "bot": bot_response})
        session["history"] = session["history"][-20:]

    # --- Main Message Processing Logic (Refactored for API) ---

    def process_chat_message(self, chat_id, user_text):
        """
        Обрабатывает текстовое сообщение и возвращает словарь с ответом и метаданными.
        """
        self.log_event(f"Received text from {chat_id}: {user_text}")

        session = self._prepare_session(chat_id)
        nlp_result = self._perform_nlp_analysis(user_text, session)

        self.log_event(f"NLP result for {chat_id}: {json.dumps(nlp_result, ensure_ascii=False, indent=2)}")

        updated_context = self.context_manager.update_context(
            current_context=session["context"],
            nlp_result=nlp_result
        )

        intent_name = nlp_result["intents"][0]["name"]
        final_response_str, _ = self._generate_response(
            chat_id, intent_name, updated_context["entities"], updated_context
        )

        session["context"] = updated_context
        self._update_history(session, user_text, final_response_str)

        # Создаем объект с интентом для возврата
        intent_object = {
            "intent": intent_name,
            "entities": updated_context["entities"],
            "dialogue_state": nlp_result.get("metadata", {}).get("raw_openai_response", {}).get("dialogue_state", "unknown")
        }

        self.log_event(f"Generated response for {chat_id}: {final_response_str}")
        return {"reply": final_response_str, "intent_object": intent_object}

    # --- Telegram Specific Methods ---

    def start_command_handler(self, message):
        self._prepare_session(message.chat.id)
        reply = "Привет! Я Katana, ваш умный ассистент."
        self.telebot.reply_to(message, reply)

    def run(self):
        if not self.telebot:
            raise Exception("Telebot not initialized. Instantiate KatanaBot with use_telebot=True.")
        self.log_event("Bot starting in Telegram polling mode...")
        self.telebot.infinity_polling()

    # --- Intent Handlers (No change) ---
    def handle_intent_get_weather(self, chat_id, entities, context):
        city = entities.get("city")
        return f"☀️ Погода в городе {city} отличная!" if city else "Для какого города вы хотите узнать погоду?"
    def handle_intent_tell_joke(self, chat_id, entities, context):
        return random.choice(["Колобок повесился.", "Почему программисты не любят темную тему? Свет притягивает баги."])
    def handle_intent_get_fact(self, chat_id, entities, context):
        return random.choice(["У улитки около 25 000 зубов."])
    def handle_intent_greeting(self, chat_id, entities, context):
        return random.choice(["Привет!", "Здравствуйте!"])
    def handle_intent_goodbye(self, chat_id, entities, context):
        return random.choice(["Пока!", "До свидания!"])
    def handle_intent_get_time(self, chat_id, entities, context):
        return f"Текущее время: {datetime.now().strftime('%H:%M:%S')}."
    def handle_intent_clarify_city_for_weather(self, chat_id, entities, context):
        return "Для какого города вы хотите узнать погоду?"
    def handle_intent_fallback_general(self, chat_id, entities, context):
        return "Я не совсем понял. Можете переформулировать?"

if __name__ == '__main__':
    bot_instance = KatanaBot(use_telebot=True)
    bot_instance.run()
