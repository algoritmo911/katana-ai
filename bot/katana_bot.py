import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import random

from bot.nlp.parser import Parser
from bot.nlp.nlp_processor import NLPProcessor
from bot.nlp.context import DialogueContextManager

class KatanaBot:
    """
    Основной класс бота, инкапсулирующий состояние и логику.
    """
    def __init__(self):
        self.nlp_processor = NLPProcessor()
        self.parser = Parser(self.nlp_processor)
        self.context_manager = DialogueContextManager()
        self.sessions = {}
        self._initialize_intent_handlers()

        self.api_token = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
        if not self.api_token or ':' not in self.api_token:
            raise ValueError("❌ Invalid or missing Telegram API token.")
        self.telebot = telebot.TeleBot(self.api_token)
        self._register_telebot_handlers()

    def _initialize_intent_handlers(self):
        """Инициализирует и регистрирует обработчики намерений."""
        self.intent_handlers = {
            "get_weather": self.handle_intent_get_weather,
            "tell_joke": self.handle_intent_tell_joke,
            "get_fact": self.handle_intent_get_fact,
            "greeting": self.handle_intent_greeting,
            "goodbye": self.handle_intent_goodbye,
            "get_time": self.handle_intent_get_time,
            "clarify_city_for_weather": self.handle_intent_clarify_city_for_weather,
            "fallback_general": self.handle_intent_fallback_general,
        }

    def _register_telebot_handlers(self):
        """Регистрирует обработчики сообщений для Telebot."""
        @self.telebot.message_handler(commands=['start', 'help'])
        def handle_start_help(message):
            self.start_command_handler(message)

        @self.telebot.message_handler(func=lambda message: message.content_type == 'text')
        def handle_user_chat_message(message):
            self.process_chat_message(message)

    def log_event(self, message_text):
        print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message_text}")

    # --- Pipeline Stages ---

    def _prepare_session(self, chat_id):
        """Готовит сессию для пользователя, создавая ее при необходимости."""
        if chat_id not in self.sessions:
            self.sessions[chat_id] = self.context_manager.get_initial_session()
        return self.sessions[chat_id]

    def _perform_nlp_analysis(self, text, session):
        """Выполняет NLP-анализ, используя историю из сессии."""
        return self.parser.analyze_text(text, history=session['history'])

    def _generate_response(self, chat_id, intent_name, merged_entities, context):
        """Генерирует ответ на основе NLP-анализа."""
        handler = self.intent_handlers.get(intent_name, self.handle_intent_fallback_general)
        response_text = handler(chat_id, merged_entities, context)
        return response_text, [{"name": intent_name, "processed": True, "response": response_text}]

    def _update_history(self, session, user_text, bot_response):
        """Обновляет историю диалога в сессии."""
        session["history"].append({"user": user_text, "bot": bot_response})
        session["history"] = session["history"][-20:]

    # --- Main Message Processing Logic ---

    def process_chat_message(self, message):
        """Основной обработчик текстовых сообщений."""
        chat_id = message.chat.id
        user_text = message.text
        self.log_event(f"Received text from {chat_id}: {user_text}")

        # 1. Подготовка сессии
        session = self._prepare_session(chat_id)

        # 2. NLP-анализ
        nlp_result = self._perform_nlp_analysis(user_text, session)
        self.log_event(f"NLP result for {chat_id}: {json.dumps(nlp_result, ensure_ascii=False, indent=2)}")

        # 3. Обновление контекста ( ДО генерации ответа)
        # Это ключевое изменение: мы получаем новый, объединенный контекст ПЕРЕД тем, как сгенерировать ответ.
        updated_context = self.context_manager.update_context(
            current_context=session["context"],
            nlp_result=nlp_result
        )

        # 4. Генерация ответа с использованием обновленного контекста
        intent_name = nlp_result["intents"][0]["name"]
        final_response_str, processed_intents_info = self._generate_response(
            chat_id, intent_name, updated_context["entities"], updated_context
        )

        # 5. Обновление состояния сессии (контекст и история)
        session["context"] = updated_context
        self._update_history(session, user_text, final_response_str)

        # 6. Отправка ответа
        if final_response_str:
            self.telebot.reply_to(message, final_response_str)
            self.log_event(f"Sent response to {chat_id}: {final_response_str}")

    def start_command_handler(self, message):
        """Обработчик команды /start."""
        self._prepare_session(message.chat.id)
        reply = "Привет! Я Katana, ваш умный ассистент."
        self.telebot.reply_to(message, reply)

    def run(self):
        """Запускает бота."""
        self.log_event("Bot starting with new Cognitive Core...")
        self.telebot.infinity_polling()

    # --- Intent Handlers ---
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
    bot_instance = KatanaBot()
    bot_instance.run()
