import telebot
import json
import os
from pathlib import Path
from datetime import datetime
import random # Для случайных ответов

# Импортируем наши NLP модули и ядро команд
from bot.nlp import parser as nlp_parser
from bot.nlp import context as nlp_context
from bot import commands as command_core

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('KATANA_TELEGRAM_TOKEN', 'YOUR_API_TOKEN')
if not API_TOKEN or ':' not in API_TOKEN:
    raise ValueError("❌ Invalid or missing Telegram API token. Please set KATANA_TELEGRAM_TOKEN env variable with format '123456:ABCDEF'.")

bot = telebot.TeleBot(API_TOKEN)

# Папка для сохранения JSON-команд (если они еще нужны)
COMMAND_FILE_DIR = Path('commands')
COMMAND_FILE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory хранилище для контекста и истории пользователей
user_memory = {}

def log_local_bot_event(message_text):
    """Вывод лога события в консоль."""
    print(f"[BOT EVENT] {datetime.utcnow().isoformat()}: {message_text}")

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    """Ответ на /start и /help"""
    chat_id = message.chat.id
    log_local_bot_event(f"{message.text} received from {chat_id}")

    # Инициализация памяти для нового пользователя
    if chat_id not in user_memory:
        user_memory[chat_id] = {
            "context": nlp_context.get_initial_context(),
            "history": []
        }

    bot.reply_to(message, "Привет! Я Katana, ваш умный ассистент. Спросите меня что-нибудь, например:\n"
                          "- Какая погода в Москве?\n"
                          "- Расскажи анекдот\n"
                          "- Который час?\n"
                          "Я стараюсь понимать несколько команд сразу и помнить наш разговор.")

# --- Этапы обработки сообщения ---

def _prepare_context(chat_id, user_text):
    """Подготовка контекста: получение или инициализация памяти пользователя."""
    if chat_id not in user_memory:
        user_memory[chat_id] = {
            "context": nlp_context.get_initial_context(),
            "history": []
        }
    return user_memory[chat_id]

def _perform_nlp_analysis(user_text, current_context):
    """NLP-анализ текста."""
    nlp_result = nlp_parser.analyze_text(user_text, current_context)
    # В будущем здесь может быть более сложная логика, включая тематические фреймы
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
        handler = command_core.get_handler("greeting")
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
                handler = command_core.get_handler(target_intent_name)
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

        handler = command_core.get_handler(intent_name)
        if handler:
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

        final_fallback_handler = command_core.get_handler(fallback_intent_name_to_use)
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

def _update_state(chat_id, user_text, final_response, session_memory, nlp_result, processed_intents_info):
    """Обновление состояния: контекст, история, логирование метрик."""
    current_context = session_memory["context"]

    # Обновляем контекст на основе результатов NLP и обработки
    session_memory["context"] = nlp_context.update_context(current_context, nlp_result, processed_intents_info)

    # Обновляем историю
    session_memory["history"].append({
        "user": user_text,
        "bot": final_response,
        "timestamp": datetime.utcnow().isoformat(),
        "nlp_result": nlp_result, # Сохраняем для возможного анализа и метрик
        "processed_intents": processed_intents_info # Детали обработки
    })
    # Ограничиваем историю
    session_memory["history"] = session_memory["history"][-20:]

    # --- Логирование метрик осознанности ---
    # Metric 1: Contextual Linkage
    # Проверяем, были ли сущности из предыдущего контекста использованы текущими обработчиками.
    # ИЛИ если активный фрейм был продолжен/завершен.
    contextual_linkage_score = 0
    prev_context_entities = current_context.get("entities", {})

    # Check if entities from previous context were used in any of the processed intents
    for p_info in processed_intents_info:
        if p_info.get("processed") and p_info.get("entities_used"):
            for entity_key, entity_value in prev_context_entities.items():
                if entity_key in p_info["entities_used"] and p_info["entities_used"][entity_key] == entity_value:
                    contextual_linkage_score += 1
                    break # Count each previous entity usage once across all processed intents

    # Check if an active frame from nlp_result was a continuation of a previous state
    # (e.g. a weather frame was incomplete and is now being completed or clarified)
    # This is a simplified check. More sophisticated frame transition tracking would be better.
    if nlp_result.get("active_frames"):
        current_frame_name = nlp_result["active_frames"][0]["name"] # Assuming one primary frame for now
        # A simple heuristic: if the last processed intent was related to this frame's clarification, it's a contextual link.
        if current_context.get("last_processed_intent") == "clarify_city_for_weather" and \
           current_frame_name == "weather_inquiry_frame" and \
           any(p_info["name"] == "get_weather" for p_info in processed_intents_info):
            contextual_linkage_score += 1 # Bonus for frame continuation

    # Metric 2: Understanding Depth
    primary_intent_name = None
    primary_intent_confidence = 0.0
    if processed_intents_info: # Use processed intents to determine primary
        # Find first non-fallback processed intent if possible
        first_real_intent_info = next((p for p in processed_intents_info if p.get("processed") and not p.get("is_final_fallback") and not p.get("name", "").startswith("fallback_")), None)
        if first_real_intent_info:
            primary_intent_name = first_real_intent_info["name"]
            # Try to get confidence from original nlp_result for this intent
            original_intent_data = next((i for i in nlp_result.get("intents", []) if i["name"] == primary_intent_name), None)
            if original_intent_data:
                primary_intent_confidence = original_intent_data.get("confidence", 0.0)
        elif processed_intents_info[0].get("processed"): # If only fallback was processed
            primary_intent_name = processed_intents_info[0]["name"]
            original_intent_data = next((i for i in nlp_result.get("intents", []) if i["name"] == primary_intent_name), None)
            if original_intent_data:
                 primary_intent_confidence = original_intent_data.get("confidence", 1.0) # Default to 1.0 for fallbacks from parser

    used_fallback_type = nlp_result.get("fallback_type") # From parser
    is_final_fallback_handler_used = any(p.get("is_final_fallback") for p in processed_intents_info)

    # Log metrics
    metrics_log = {
        "chat_id": chat_id,
        "contextual_linkage_score": contextual_linkage_score,
        "primary_intent_name": primary_intent_name,
        "primary_intent_confidence": f"{primary_intent_confidence:.2f}",
        "used_fallback_type": used_fallback_type, # Fallback type identified by parser
        "is_final_fallback_handler_used": is_final_fallback_handler_used, # If _generate_response used its own fallback
        "active_frames_count": len(nlp_result.get("active_frames", []))
    }
    log_local_bot_event(f"KATANA_METRICS: {json.dumps(metrics_log)}")
    log_local_bot_event(f"Updated memory for {chat_id}: {json.dumps(session_memory, ensure_ascii=False, indent=2, default=str)}")

@bot.message_handler(func=lambda message: message.content_type == 'text')
def handle_user_chat_message(message):
    """
    Обработчик текстовых сообщений от пользователя с использованием NLP.
    Разбит на этапы: подготовка контекста -> NLP-анализ -> генерация ответа -> сохранение состояния.
    """
    chat_id = message.chat.id
    user_text = message.text
    log_local_bot_event(f"Received text from {chat_id}: {user_text}")

    # 1. Подготовка контекста
    session_memory = _prepare_context(chat_id, user_text)
    current_context = session_memory["context"] # Берем актуальный контекст после подготовки

    # 2. NLP-анализ
    # Передаем оригинальный user_text и current_context (который может быть только что инициализирован)
    nlp_result = _perform_nlp_analysis(user_text, current_context)
    log_local_bot_event(f"NLP result for {chat_id}: {json.dumps(nlp_result, ensure_ascii=False, indent=2, default=str)}")

    # 3. Генерация ответа
    # current_context здесь - это контекст *до* обработки текущего сообщения.
    final_response_str, processed_intents_info = _generate_response(chat_id, nlp_result, current_context)

    # Отправка ответа пользователю
    if final_response_str: # Убедимся, что есть что отправлять
        bot.reply_to(message, final_response_str)
        log_local_bot_event(f"Sent response to {chat_id}: {final_response_str}")
    else:
        log_local_bot_event(f"Warning: No response generated for {chat_id} with text '{user_text}'")
        # Можно отправить стандартный fallback, если _generate_response вернул пустую строку,
        # но по идее, _generate_response всегда должен что-то возвращать (хотя бы fallback).

    # 4. Обновление состояния (контекст, история, метрики)
    # session_memory передается для модификации напрямую.
    # nlp_result и processed_intents_info нужны для обновления контекста и истории.
    _update_state(chat_id, user_text, final_response_str, session_memory, nlp_result, processed_intents_info)


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