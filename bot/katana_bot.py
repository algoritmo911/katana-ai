import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import random
from dotenv import load_dotenv

# Загружаем переменные окружения в самом начале
load_dotenv()

# Импортируем наши модули
from bot.nlp import parser as nlp_parser
from bot.nlp import context as nlp_context
from bot import database

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN')
bot = None
if API_TOKEN and ':' in API_TOKEN:
    bot = telebot.TeleBot(API_TOKEN)
else:
    print("WARNING: Telegram API token not found. Bot instance not created. Running in test mode or without Telegram integration.")

# Папка для сохранения JSON-команд (если они еще нужны)
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory хранилище user_memory УДАЛЕНО. Теперь все будет в Supabase.

def log_local_bot_event(message_text):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message_text}")

# --- Заглушки для обработки намерений ---
def handle_intent_get_weather(chat_id, entities, current_context):
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

def handle_intent_fallback_general(chat_id, entities, current_context):
    """Обработчик для общего fallback."""
    options = [
        "Я не совсем понял, что вы имеете в виду. Можете переформулировать?",
        "Хм, я пока не умею на это отвечать. Попробуйте что-нибудь другое.",
        "Извините, я не распознал вашу команду. Может, попробуем что-то из этого: погода, факт, анекдот?"
    ]
    return random.choice(options)

def handle_intent_fallback_clarification_needed(chat_id, entities, current_context):
    """Обработчик для fallback, когда нужны уточнения."""
    # entities в nlp_result могут помочь дать более конкретный ответ
    recognized_entities_parts = []
    if entities.get("city"):
        recognized_entities_parts.append(f"город {entities['city']}")
    # Можно добавить другие сущности по мере их появления

    if recognized_entities_parts:
        return f"Я понял, что речь идет о {', '.join(recognized_entities_parts)}, но не совсем ясно, что вы хотите. Можете уточнить?"
    else:
        # Если сущностей нет, но этот fallback вызван, это странно, но дадим общий ответ.
        return "Мне кажется, я уловил часть информации, но не могу понять запрос целиком. Пожалуйста, уточните."


def handle_intent_fallback_after_clarification_fail(chat_id, entities, current_context):
    return "Я все еще не понял, какой город вас интересует. Давайте попробуем другую команду?"

def _handle_intent_recall_information(chat_id, nlp_result):
    """
    Обрабатывает запрос на извлечение информации из памяти (БД).
    """
    keywords = nlp_result.get("metadata", {}).get("keywords", [])
    if not keywords:
        return "Я не совсем понял, о чем вы спрашиваете. Можете уточнить?"

    # Ищем релевантные сообщения в истории
    relevant_messages = database.search_messages_by_keywords(chat_id, keywords)

    if not relevant_messages:
        return "Хм, я не могу вспомнить, чтобы мы об этом говорили."

    # Очень простая логика ответа: берем последнее релевантное сообщение
    # и пытаемся извлечь из него ответ на основе сущностей в вопросе.
    last_relevant_message_meta = relevant_messages[-1].get("metadata", {})
    question_entities = nlp_result.get("entities", {})

    # Если в вопросе есть "город" или "куда" (что NLP определит как LOC)
    if "city" in question_entities or "loc" in question_entities:
        # Ищем сущность LOC в найденном сообщении
        found_entities = last_relevant_message_meta.get("raw_entities", [])
        for entity in found_entities:
            if entity.get("type") == "LOC":
                return f"Вы планировали что-то в городе {entity.get('text')}."

    # Если в вопросе есть "кто" или "с кем" (PERSON)
    if "person" in question_entities:
        found_entities = last_relevant_message_meta.get("raw_entities", [])
        for entity in found_entities:
            if entity.get("type") == "PERSON":
                return f"В планах упоминался(-ась) {entity.get('text')}."

    # Если не удалось найти конкретный ответ, но есть релевантное сообщение
    return f"Я помню, мы обсуждали это. Вот что вы сказали: \"{relevant_messages[-1].get('user_text')}\""


# Маппинг намерений на их обработчики
INTENT_HANDLERS = {
    "get_weather": handle_intent_get_weather,
    "tell_joke": handle_intent_tell_joke,
    "get_fact": handle_intent_get_fact,
    "greeting": handle_intent_greeting,
    "goodbye": handle_intent_goodbye,
    "get_time": handle_intent_get_time,
    "recall_information": _handle_intent_recall_information,
    "clarify_city_for_weather": handle_intent_clarify_city_for_weather,
    "fallback_general": handle_intent_fallback_general, # Изменено с "fallback"
    "fallback_clarification_needed": handle_intent_fallback_clarification_needed, # Новый обработчик
    "fallback_after_clarification_fail": handle_intent_fallback_after_clarification_fail,
}

if bot:
    @bot.message_handler(commands=['start', 'help'])
    def handle_start_help(message):
        """Ответ на /start и /help"""
        chat_id = message.chat.id
        log_local_bot_event(f"{message.text} received from {chat_id}")

        # Инициализация памяти больше не нужна, т.к. контекст будет создаваться на лету из БД

        bot.reply_to(message, "Привет! Я Katana, ваш умный ассистент. Спросите меня что-нибудь, например:\n"
                            "- Какая погода в Москве?\n"
                            "- Расскажи анекдот\n"
                            "- Который час?\n"
                            "Я стараюсь понимать несколько команд сразу и помнить наш разговор.")

# --- Этапы обработки сообщения ---

def _prepare_context(chat_id, user_text):
    """
    Подготовка контекста: извлечение истории из БД и построение текущего контекста.
    Возвращает текущий контекст (не всю историю).
    """
    # Извлекаем недавнюю историю, чтобы построить контекст
    recent_messages = database.get_recent_messages(chat_id, limit=5)

    # Если истории нет, возвращаем начальный контекст
    if not recent_messages:
        return nlp_context.get_initial_context()

    # Строим простой контекст на основе последнего сообщения в истории
    # В будущем эту логику можно усложнить, анализируя несколько последних сообщений
    last_message = recent_messages[-1]
    last_metadata = last_message.get('metadata', {})

    # Используем нашу функцию из nlp_context для создания контекста из старых данных
    # Это примерная логика. nlp_context.update_context ожидает nlp_result и processed_intents
    # Мы можем эмулировать это или создать новую функцию.
    # Пока что, просто возьмем сущности и последний интент из метаданных.

    reconstructed_context = nlp_context.get_initial_context()
    if last_metadata:
        # Предполагаем, что в metadata есть `raw_intent` и `raw_entities`
        last_intent = last_metadata.get('raw_intent')
        if last_intent:
            reconstructed_context['last_recognized_intent'] = last_intent

        # Преобразуем список сущностей в словарь, как ожидает контекст
        last_entities_list = last_metadata.get('raw_entities', [])
        reconstructed_entities = {}
        for entity in last_entities_list:
            entity_type = entity.get("type", "").lower()
            if entity_type == "loc":
                reconstructed_entities["city"] = entity.get("text")
            else:
                reconstructed_entities[entity_type] = entity.get("text")
        reconstructed_context['entities'] = reconstructed_entities

    log_local_bot_event(f"Reconstructed context for {chat_id}: {reconstructed_context}")
    return reconstructed_context


def _perform_nlp_analysis(user_text, current_context):
    """NLP-анализ текста."""
    # `current_context` теперь приходит из _prepare_context, который построил его из БД
    nlp_result = nlp_parser.analyze_text(user_text, current_context)
    return nlp_result

def _generate_response(chat_id, nlp_result, current_context):
    """Генерация ответа на основе NLP-анализа."""
    bot_responses = []
    processed_intents_info = []

    # Гарантируем наличие fallback интента, если NLP ничего не вернул
    bot_responses = []
    processed_intents_info = []

    intents_from_nlp = nlp_result.get("intents", [])
    active_frames_from_nlp = nlp_result.get("active_frames", [])
    entities_from_nlp = nlp_result.get("entities", {})

    processed_intent_names_this_turn = set()

    greeting_response_text = None
    greeting_processed_info = None

    # 1. Handle Greeting first and separately if present
    # Create a mutable list of intents to allow removal of the greeting intent
    mutable_intents_list = [intent for intent in intents_from_nlp if isinstance(intent, dict) and intent.get("name")]

    greeting_intent_data = next((item for item in mutable_intents_list if item["name"] == "greeting"), None)
    if greeting_intent_data:
        handler = INTENT_HANDLERS.get("greeting")
        if handler:
            greeting_response_text = handler(chat_id, entities_from_nlp, current_context)
            greeting_processed_info = {
                "name": "greeting", "processed": True, "response": greeting_response_text,
                "entities_used": {}
                # "is_greeting_multi" will be set later if other responses are generated
            }
            processed_intent_names_this_turn.add("greeting")
            mutable_intents_list = [item for item in mutable_intents_list if item["name"] != "greeting"]


    # 2. Frame-driven response logic
    frame_responses = []
    frame_processed_infos = []

    if active_frames_from_nlp:
        primary_frame = active_frames_from_nlp[0]
        if primary_frame["name"] == "weather_inquiry_frame":
            target_intent_name = None
            if primary_frame["status"] == "incomplete":
                target_intent_name = "clarify_city_for_weather"
            elif primary_frame["status"] in ["ready_to_fulfill", "completed_after_clarification"]:
                target_intent_name = "get_weather"

            if target_intent_name and target_intent_name not in processed_intent_names_this_turn:
                handler = INTENT_HANDLERS.get(target_intent_name)
                if handler:
                    response_text = handler(chat_id, entities_from_nlp, current_context)
                    frame_responses.append(response_text)
                    frame_processed_infos.append({
                        "name": target_intent_name, "processed": True, "response": response_text,
                        "entities_used": entities_from_nlp, "triggered_by_frame": primary_frame["name"]
                    })
                    processed_intent_names_this_turn.add(target_intent_name)

    # 3. Process other remaining intents
    other_intent_responses = []
    other_intent_processed_infos = []

    for intent_data in mutable_intents_list: # mutable_intents_list now excludes greeting if handled
        intent_name = intent_data["name"]
        if intent_name in processed_intent_names_this_turn: # Skip if handled by frame
            continue

        handler = INTENT_HANDLERS.get(intent_name)
        if handler:
            if handler is _handle_intent_recall_information:
                # Этот обработчик имеет другую сигнатуру
                response_text = handler(chat_id, nlp_result)
            else:
                response_text = handler(chat_id, entities_from_nlp, current_context)

            other_intent_responses.append(response_text)
            other_intent_processed_infos.append({
                "name": intent_name, "processed": True, "response": response_text,
                "entities_used": entities_from_nlp
            })
            processed_intent_names_this_turn.add(intent_name)
        else:
            log_local_bot_event(f"Warning: No handler for intent '{intent_name}' (other_intent_loop) for chat_id {chat_id}")
            other_intent_processed_infos.append({"name": intent_name, "processed": False})

    # Combine responses and processed_info
    # Order: Greeting (if any), then Frame responses, then Other intent responses
    if greeting_response_text:
        bot_responses.append(greeting_response_text)
        # Update is_greeting_multi if other responses exist
        if frame_responses or other_intent_responses:
            greeting_processed_info["is_greeting_multi"] = True
        processed_intents_info.append(greeting_processed_info)

    bot_responses.extend(frame_responses)
    processed_intents_info.extend(frame_processed_infos)

    bot_responses.extend(other_intent_responses)
    processed_intents_info.extend(other_intent_processed_infos)

    # 4. Final Fallback (if bot_responses is still empty after all attempts)
    if not bot_responses: # Check if any response was generated
        log_local_bot_event(f"Info: No specific intents or frames led to a response for chat_id {chat_id}. Determining fallback.")

        fallback_intent_name_to_use = "fallback_general" # Default
        if nlp_result.get("fallback_type"):
            if nlp_result["fallback_type"] == "clarification_needed":
                fallback_intent_name_to_use = "fallback_clarification_needed"
            elif nlp_result["fallback_type"] == "clarification_failed":
                 fallback_intent_name_to_use = "fallback_after_clarification_fail"

        final_fallback_handler = INTENT_HANDLERS.get(fallback_intent_name_to_use)
        if final_fallback_handler:
            fallback_response_text = final_fallback_handler(chat_id, entities_from_nlp, current_context)
            bot_responses.append(fallback_response_text)
            processed_intents_info.append({
                "name": fallback_intent_name_to_use, "processed": True, "response": fallback_response_text,
                "is_final_fallback": True, "entities_used": entities_from_nlp
            })
        else: # Should not happen if INTENT_HANDLERS is comprehensive for fallbacks
            log_local_bot_event(f"CRITICAL: Fallback handler for '{fallback_intent_name_to_use}' not found!")
            # Default to a very basic message if even fallback_general is missing
            bot_responses.append("Что-то пошло совсем не так, я не смог подобрать ответ.")
            processed_intents_info.append({
                "name": "critical_fallback", "processed": True, "response": bot_responses[-1],
                "is_final_fallback": True, "entities_used": {}
            })

    final_response_string = "\n".join(filter(None, bot_responses)) # filter(None,...) in case a handler returns None
    return final_response_string, processed_intents_info

def _update_state(chat_id, user_text, final_response, nlp_result):
    """
    Обновление состояния: сохранение сообщения и его метаданных в Supabase.
    """
    # Создаем копию метаданных, чтобы избежать циклических ссылок
    metadata_to_save = nlp_result.get("metadata", {}).copy()

    # Создаем копию всего nlp_result, чтобы не изменять оригинал
    clean_nlp_result = nlp_result.copy()
    # Удаляем из копии ключ 'metadata', чтобы избежать цикла при сериализации
    clean_nlp_result.pop('metadata', None)

    # Добавляем очищенный результат в метаданные для сохранения
    metadata_to_save['full_nlp_result'] = clean_nlp_result

    database.save_message(
        chat_id=chat_id,
        user_text=user_text,
        bot_response=final_response,
        metadata=metadata_to_save
    )
    # Логируем только после успешного сохранения
    log_local_bot_event(f"State saved to DB for chat_id {chat_id}.")


def process_message_logic(chat_id, user_text):
    """
    Основная логика обработки сообщения, вынесенная для тестирования.
    Возвращает финальный ответ бота.
    """
    log_local_bot_event(f"Processing text for {chat_id}: {user_text}")

    # 1. Подготовка контекста из БД
    current_context = _prepare_context(chat_id, user_text)

    # 2. NLP-анализ
    nlp_result = _perform_nlp_analysis(user_text, current_context)
    log_local_bot_event(f"NLP result for {chat_id}: {json.dumps(nlp_result, ensure_ascii=False, indent=2, default=str)}")

    # 3. Генерация ответа
    final_response_str, processed_intents_info = _generate_response(chat_id, nlp_result, current_context)

    # 4. Обновление состояния (сохранение в БД)
    _update_state(chat_id, user_text, final_response_str, nlp_result)

    return final_response_str


if bot:
    @bot.message_handler(func=lambda message: message.content_type == 'text')
    def handle_user_chat_message(message):
        """
        Обработчик текстовых сообщений от пользователя.
        Вызывает основную логику и отправляет ответ.
        """
        chat_id = message.chat.id
        user_text = message.text

        final_response_str = process_message_logic(chat_id, user_text)

        # Отправка ответа пользователю
        if final_response_str:
            bot.reply_to(message, final_response_str)
            log_local_bot_event(f"Sent response to {chat_id}: {final_response_str}")
        else:
            log_local_bot_event(f"Warning: No response generated for {chat_id} with text '{user_text}'")


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
    # bot.polling() # Запуск бота будет осуществляться другим способом при тестировании
    # Для локального запуска можно раскомментировать:
    # bot.infinity_polling(logger_level=None) # Используем infinity_polling для более стабильной работы
    # log_local_bot_event("Bot stopped.")
    print("Bot initialized. To run, call bot.infinity_polling()")