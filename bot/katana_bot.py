import telebot
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import random # Для случайных ответов
import threading

# Импортируем наши NLP модули
from bot.nlp import parser as nlp_parser
from bot.nlp import context as nlp_context
from bot import autosuggest

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN)

# Папка для сохранения JSON-команд (если они еще нужны)
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory хранилище для контекста и истории пользователей
# user_memory = {} # Заменено на загрузку из файла

# --- Управление состоянием пользователя ---
USER_STATE_FILE = Path('user_state.json')
user_memory = {} # Будет загружено из файла

# --- Логика авто-подсказок ---
INACTIVITY_DELAY_SECONDS = 15 # Время в секундах для срабатывания подсказки
user_suggestion_timers = {} # Словарь для хранения таймеров для каждого чата

def load_user_state():
    """Загружает состояние пользователей из файла."""
    global user_memory
    if USER_STATE_FILE.exists():
        try:
            with open(USER_STATE_FILE, 'r', encoding='utf-8') as f:
                user_memory = json.load(f)
                # Ключи в JSON всегда строки, преобразуем chat_id обратно в int, если это возможно
                user_memory = {int(k) if k.isdigit() else k: v for k, v in user_memory.items()}
                log_local_bot_event(f"User state loaded from {USER_STATE_FILE}")
        except (json.JSONDecodeError, IOError) as e:
            log_local_bot_event(f"Error loading user state from {USER_STATE_FILE}: {e}. Starting with empty state.")
            user_memory = {}
    else:
        log_local_bot_event(f"User state file {USER_STATE_FILE} not found. Starting with empty state.")
        user_memory = {}

def save_user_state():
    """Сохраняет текущее состояние пользователей в файл."""
    global user_memory
    try:
        with open(USER_STATE_FILE, 'w', encoding='utf-8') as f:
            # Конвертируем числовые chat_id в строки для совместимости с JSON
            memory_to_save = {str(k): v for k, v in user_memory.items()}
            json.dump(memory_to_save, f, ensure_ascii=False, indent=4)
            log_local_bot_event(f"User state saved to {USER_STATE_FILE}")
    except IOError as e:
        log_local_bot_event(f"Error saving user state to {USER_STATE_FILE}: {e}")


def log_local_bot_event(message_text):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message_text}")

# --- Функции для авто-подсказок ---
def send_suggestion(chat_id):
    """Отправляет подсказку пользователю, если он неактивен."""
    log_local_bot_event(f"User {chat_id} is inactive, preparing suggestion.")

    if chat_id in user_memory:
        current_session_memory = user_memory[chat_id]
        suggestions = autosuggest.get_suggestions(
            current_session_memory.get("context", {}),
            current_session_memory.get("history", [])
        )

        if suggestions:
            markup = telebot.types.InlineKeyboardMarkup()
            for sug in suggestions:
                button = telebot.types.InlineKeyboardButton(text=sug["text"], callback_data=sug["callback_data"])
                markup.add(button)

            try:
                bot.send_message(chat_id, "Может, попробуем что-нибудь из этого?", reply_markup=markup)
                log_local_bot_event(f"Sent suggestion to {chat_id}.")
            except Exception as e:
                log_local_bot_event(f"Failed to send suggestion to {chat_id}: {e}")

def schedule_suggestion(chat_id):
    """Планирует отправку подсказки, отменяя предыдущую."""
    cancel_suggestion(chat_id) # Отменяем предыдущий таймер, если он есть

    timer = threading.Timer(INACTIVITY_DELAY_SECONDS, send_suggestion, args=[chat_id])
    user_suggestion_timers[chat_id] = timer
    timer.start()
    log_local_bot_event(f"Suggestion scheduled for chat_id {chat_id} in {INACTIVITY_DELAY_SECONDS}s.")

def cancel_suggestion(chat_id):
    """Отменяет запланированную подсказку."""
    if chat_id in user_suggestion_timers:
        user_suggestion_timers[chat_id].cancel()
        del user_suggestion_timers[chat_id]
        log_local_bot_event(f"Suggestion cancelled for chat_id {chat_id}.")

# --- Заглушки для обработки намерений ---
def handle_intent_get_weather(chat_id, entities, current_context):
    log_local_bot_event(f"[get_weather] Received entities: {entities}, Current context entities: {current_context.get('entities')}")
    city = entities.get("city")
    if city:
        return f"☀️ Погода в городе {city} отличная! (но это не точно)"
    else:
        # Это состояние должно было быть обработано в nlp_parser для создания clarify_city_for_weather
        return "Хм, кажется, я должен был спросить город, но что-то пошло не так."

def handle_intent_tell_joke(chat_id, entities, current_context):
    jokes = [
        "Колобок повесился.",
        "Почему программисты предпочитают темную тему? Потому что свет притягивает баги!",
        "Заходит улитка в бар..."
    ]
    return random.choice(jokes)

def handle_intent_get_fact(chat_id, entities, current_context):
    facts = [
        "Медведи могут лазить по деревьям.",
        "Самый долгий полет курицы — 13 секунд.",
        "У улитки около 25 000 зубов."
    ]
    return random.choice(facts)

def handle_intent_greeting(chat_id, entities, current_context):
    return random.choice(["Привет!", "Здравствуйте!", "Рад вас снова видеть!"])

def handle_intent_goodbye(chat_id, entities, current_context):
    return random.choice(["Пока!", "До свидания!", "Надеюсь, скоро увидимся."])

def handle_intent_get_time(chat_id, entities, current_context):
    now = datetime.now()
    return f"Текущее время: {now.strftime('%H:%M:%S')}."

def handle_intent_clarify_city_for_weather(chat_id, entities, current_context):
    return "Для какого города вы хотите узнать погоду?"

def handle_intent_fallback(chat_id, entities, current_context):
    options = [
        "Я не совсем понял, что вы имеете в виду. Можете переформулировать?",
        "Хм, я пока не умею на это отвечать. Попробуйте что-нибудь другое.",
        "Извините, я не распознал вашу команду."
    ]
    return random.choice(options)

def handle_intent_fallback_after_clarification_fail(chat_id, entities, current_context):
    return "Я все еще не понял, какой город вас интересует. Давайте попробуем другую команду?"

# Маппинг намерений на их обработчики
INTENT_HANDLERS = {
    "get_weather": handle_intent_get_weather,
    "tell_joke": handle_intent_tell_joke,
    "get_fact": handle_intent_get_fact,
    "greeting": handle_intent_greeting,
    "goodbye": handle_intent_goodbye,
    "get_time": handle_intent_get_time,
    "clarify_city_for_weather": handle_intent_clarify_city_for_weather,
    "fallback": handle_intent_fallback,
    "fallback_after_clarification_fail": handle_intent_fallback_after_clarification_fail,
}

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    """Ответ на /start и /help"""
    chat_id = message.chat.id
    log_local_bot_event(f"{message.text} received from {chat_id}")

    # Инициализация памяти для нового пользователя
    if chat_id not in user_memory:
        user_memory[chat_id] = {
            "context": nlp_context.get_initial_context(),
            "history": [],
            "settings": {}, # Добавляем placeholder для настроек пользователя
            "last_interaction_time": datetime.utcnow().isoformat()
        }
        log_local_bot_event(f"Initialized new memory structure for chat_id {chat_id} including settings.")

    bot.reply_to(message, "Привет! Я Katana, ваш умный ассистент. Спросите меня что-нибудь, например:\n"
                          "- Какая погода в Москве?\n"
                          "- Расскажи анекдот\n"
                          "- Который час?\n"
                          "Я стараюсь понимать несколько команд сразу и помнить наш разговор.")

@bot.message_handler(func=lambda message: message.content_type == 'text')
def handle_user_chat_message(message):
    """Обработчик текстовых сообщений от пользователя с использованием NLP."""
    chat_id = message.chat.id
    user_text = message.text

    log_local_bot_event(f"Received text from {chat_id}: {user_text}")

    # Получаем или инициализируем память для пользователя
    if chat_id not in user_memory:
        user_memory[chat_id] = {
            "context": nlp_context.get_initial_context(),
            "history": [],
            "settings": {} # Добавляем placeholder для настроек пользователя
        }
        log_local_bot_event(f"Initialized new memory structure for chat_id {chat_id} including settings.")

    current_session_memory = user_memory[chat_id]
    # Убедимся, что у существующих пользователей тоже есть поле settings, если оно было добавлено после их создания
    if "settings" not in current_session_memory:
        current_session_memory["settings"] = {}
        log_local_bot_event(f"Added missing 'settings' field to existing user data for chat_id {chat_id}.")
    current_context = current_session_memory["context"]

    # Анализируем текст с помощью NLP
    nlp_result = nlp_parser.analyze_text(user_text, current_context)
    log_local_bot_event(f"NLP result for {chat_id}: {json.dumps(nlp_result, ensure_ascii=False, indent=2)}")

    bot_responses = []
    processed_intents_info = [] # Для обновления контекста

    if not nlp_result["intents"]: # Дополнительная подстраховка, хотя parser должен всегда возвращать fallback
        nlp_result["intents"].append({"name": "fallback", "confidence": 1.0})

    # Обработка намерений (включая multi-intent)
    # Пока что просто проходимся по всем и выполняем, если есть обработчик
    # В более сложной системе может быть приоритезация или подтверждение
    unique_intent_names = []
    for intent_data in nlp_result["intents"]:
        if intent_data["name"] not in unique_intent_names:
             unique_intent_names.append(intent_data["name"])

    for intent_name in unique_intent_names:
        handler = INTENT_HANDLERS.get(intent_name)
        if handler:
            response = handler(chat_id, nlp_result.get("entities", {}), current_context)
            bot_responses.append(response)
            processed_intents_info.append({"name": intent_name, "processed": True, "response": response})
        else:
            log_local_bot_event(f"Warning: No handler for intent '{intent_name}' for chat_id {chat_id}")
            processed_intents_info.append({"name": intent_name, "processed": False})


    if not bot_responses: # Если ни один обработчик не сработал (маловероятно с fallback)
        bot_responses.append(INTENT_HANDLERS["fallback"](chat_id, {}, current_context))
        processed_intents_info.append({"name": "fallback", "processed": True, "response": bot_responses[-1]})

    final_response = "\n".join(bot_responses)
    bot.reply_to(message, final_response)
    log_local_bot_event(f"Sent response to {chat_id}: {final_response}")

    # Обновляем контекст и историю
    current_session_memory["context"] = nlp_context.update_context(current_context, nlp_result, processed_intents_info)
    current_session_memory["history"].append({"user": user_text, "bot": final_response, "timestamp": datetime.utcnow().isoformat()})
    current_session_memory["last_interaction_time"] = datetime.utcnow().isoformat()
    # Ограничим историю, чтобы не росла бесконечно (например, последние 20 обменов)
    current_session_memory["history"] = current_session_memory["history"][-20:]

    log_local_bot_event(f"Updated memory for {chat_id}: {json.dumps(current_session_memory, ensure_ascii=False, indent=2)}")
    save_user_state() # Сохраняем состояние после каждого сообщения

    # Планируем следующую подсказку
    schedule_suggestion(chat_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('suggest_'))
def handle_suggestion_callback(call):
    """Обрабатывает нажатия на кнопки с подсказками."""
    chat_id = call.message.chat.id
    callback_data = call.data
    log_local_bot_event(f"Received suggestion callback from {chat_id}: {callback_data}")

    # Убираем клавиатуру с подсказками
    bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)

    # Имитируем сообщение от пользователя на основе подсказки
    # Это позволяет повторно использовать существующую логику обработки сообщений
    SUGGESTION_TO_TEXT = {
        "suggest_weather": "Какая погода?",
        "suggest_weather_new_city": "Какая погода в другом городе?",
        "suggest_weather_london": "погода в Лондоне",
        "suggest_joke": "Расскажи анекдот",
        "suggest_fact": "Расскажи интересный факт",
        "suggest_get_time": "Который час?",
        "suggest_anything_else": "Что ты еще умеешь?",
        "suggest_cancel_weather": "отмена",
        "suggest_help": "/help",
    }

    user_text = SUGGESTION_TO_TEXT.get(callback_data)

    if user_text:
        # Создаем фейковый объект сообщения, чтобы передать его в обработчик
        fake_message = telebot.types.Message(
            message_id=call.message.message_id + 1, # Просто чтобы был другой ID
            from_user=call.from_user,
            date=int(datetime.utcnow().timestamp()),
            chat=call.message.chat,
            content_type='text',
            options={'text': user_text},
            json_string=""
        )
        fake_message.text = user_text

        bot.send_message(chat_id, f"Вы выбрали: '{user_text}'")
        handle_user_chat_message(fake_message)
    else:
        bot.answer_callback_query(call.id, text="Неизвестная подсказка.", show_alert=True)
        log_local_bot_event(f"Unknown suggestion callback: {callback_data}")


# --- Старая логика обработки JSON-команд (пока оставим, но она не будет вызываться обычными текстовыми сообщениями) ---
# Чтобы ее вызвать, можно сделать отдельный message_handler или изменить текущий, чтобы он проверял, является ли text валидным JSON
# Например, можно добавить команду /process_json <JSON_PAYLOAD>

def handle_json_command_message(message):
    """Обработчик для явных JSON-команд (если потребуется)."""
    chat_id = message.chat.id
    command_text = message.text # Предполагается, что это JSON-строка

    log_local_bot_event(f"Received JSON command from {chat_id}: {command_text}")

    try:
        command_data = json.loads(command_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Error: Invalid JSON format for command.")
        log_local_bot_event(f"Invalid JSON command from {chat_id}: {command_text}")
        return

    # ... (здесь остальная часть валидации и обработки JSON-команд из оригинального handle_message)
    # ... (я не буду копировать ее сюда полностью для краткости, но она должна быть здесь)

    required_fields = {
        "type": str,
        "module": str,
        "args": dict,
        "id": (str, int)
    }

    for field, expected_type in required_fields.items():
        if field not in command_data:
            error_msg = f"❌ Error: Missing required field '{field}'."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return
        if field == "id":
            if not any(isinstance(command_data[field], t) for t in expected_type):
                error_msg = f"❌ Error: Field '{field}' must be type str or int. Got {type(command_data[field]).__name__}."
                bot.reply_to(message, error_msg)
                log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
                return
        elif not isinstance(command_data[field], expected_type):
            error_msg = f"❌ Error: Field '{field}' must be type {expected_type.__name__}. Got {type(command_data[field]).__name__}."
            bot.reply_to(message, error_msg)
            log_local_bot_event(f"Validation failed for {chat_id}: {error_msg} (Command: {command_text})")
            return

    command_type = command_data.get("type")

    # Заглушки для log_event и mind_clearing (если они все еще нужны как JSON команды)
    if command_type == "log_event": # handle_log_event(command_data, chat_id)
        log_local_bot_event(f"JSON command 'log_event' called for chat_id {chat_id} with data: {command_data}")
        bot.reply_to(message, "✅ JSON 'log_event' processed (placeholder).")
        return
    elif command_type == "mind_clearing": # handle_mind_clearing(command_data, chat_id)
        log_local_bot_event(f"JSON command 'mind_clearing' called for chat_id {chat_id} with data: {command_data}")
        bot.reply_to(message, "✅ JSON 'mind_clearing' processed (placeholder).")
        return

    log_local_bot_event(f"JSON Command type '{command_type}' not specifically handled, proceeding with default save.")

    timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
    command_file_name = f"json_cmd_{timestamp_str}_{chat_id}.json"

    module_name = command_data.get('module', 'telegram_general_json')
    module_command_dir = COMMAND_FILE_DIR / f"telegram_mod_{module_name}" if module_name != 'telegram_general_json' else COMMAND_FILE_DIR / 'telegram_general_json'
    module_command_dir.mkdir(parents=True, exist_ok=True)
    command_file_path = module_command_dir / command_file_name

    with open(command_file_path, "w", encoding="utf-8") as f:
        json.dump(command_data, f, ensure_ascii=False, indent=2)

    bot.reply_to(message, f"✅ JSON Command received and saved as `{command_file_path}`.")
    log_local_bot_event(f"Saved JSON command from {chat_id} to {command_file_path}")


if __name__ == '__main__':
    log_local_bot_event("Bot starting with NLP capabilities...")
    load_user_state() # Загружаем состояние при старте
    # bot.polling() # Запуск бота будет осуществляться другим способом при тестировании
    # Для локального запуска можно раскомментировать:
    # try:
    #     bot.infinity_polling(logger_level=None) # Используем infinity_polling для более стабильной работы
    # finally:
    #     save_user_state() # Сохраняем состояние при штатном завершении
    #     log_local_bot_event("Bot stopped and user state saved.")
    print("Bot initialized. To run, call bot.infinity_polling() after ensuring load_user_state() is called.")
    print("Make sure to handle graceful shutdown to save state if running polling.")