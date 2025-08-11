# bot/nlp/parser.py
import re
from .nlp_processor import NLPProcessor, NLPError

import functools

_nlp_processor_instance = None

@functools.lru_cache(maxsize=1)
def get_nlp_processor():
    """
    Инициализирует и возвращает синглтон-экземпляр NLPProcessor.
    """
    global _nlp_processor_instance
    if _nlp_processor_instance:
        return _nlp_processor_instance

    try:
        _nlp_processor_instance = NLPProcessor()
        return _nlp_processor_instance
    except ValueError as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать NLPProcessor. {e}")
        return None

def analyze_text(text, current_context):
    """
    Анализирует текст пользователя, используя NLPProcessor для семантического анализа,
    и дополняет его существующей логикой для обратной совместимости.
    """
    nlp_processor = get_nlp_processor()
    if not nlp_processor:
        # Возвращаем структуру ошибки, если процессор не был инициализирован
        return {
            "text": text,
            "intents": [{"name": "fallback_general", "confidence": 1.0}],
            "entities": {},
            "active_frames": [],
            "fallback_type": "general",
            "error": "NLP processor is not available."
        }

    try:
        # 1. Получаем семантический анализ от NLPProcessor
        nlp_data = nlp_processor.process_text(text)
    except NLPError as e:
        print(f"ОШИБКА NLP: {e}")
        # В случае ошибки NLP, возвращаем fallback
        return {
            "text": text,
            "intents": [{"name": "fallback_general", "confidence": 1.0}],
            "entities": {},
            "active_frames": [],
            "fallback_type": "general",
            "error": str(e)
        }

    # 2. Адаптируем полученные данные к старой структуре

    # Намерение (intent)
    # nlp_data['intent'] - это строка, а нам нужен список словарей
    intent_name = nlp_data.get("intent", "fallback_general")
    # Простое сопоставление, в будущем можно сделать более сложным
    # Например, если intent от OpenAI "weather_inquiry", а у нас он называется "get_weather"
    if "погод" in intent_name.lower() or "weather" in intent_name.lower():
         intent_name = "get_weather"

    intents = [{"name": intent_name, "confidence": 1.0}] # Уверенность 1.0, т.к. это от GPT

    # Сущности (entities)
    # nlp_data['entities'] - это список словарей, а нам нужен словарь вида {"тип": "значение"}
    entities = {}
    for entity in nlp_data.get("entities", []):
        entity_type = entity.get("type", "").lower()
        # Простое сопоставление типов. LOC -> city
        if entity_type == "loc":
            entities["city"] = entity.get("text")
        else:
            entities[entity_type] = entity.get("text")

    # Добавляем остальные данные из nlp_data в корневой объект для сохранения в БД
    result = {
        "text": text,
        "intents": intents,
        "entities": entities,
        "active_frames": [],
        "fallback_type": None,
        "metadata": { # Вкладываем сырые данные от NLP сюда
            "keywords": nlp_data.get("keywords", []),
            "sentiment": nlp_data.get("sentiment", "neutral"),
            "raw_intent": nlp_data.get("intent"),
            "raw_entities": nlp_data.get("entities", [])
        }
    }

    # 3. Интегрируем старую логику для обратной совместимости (погода)
    is_get_weather_intent = any(intent["name"] == "get_weather" for intent in result["intents"])

    if is_get_weather_intent and not result["entities"].get("city"):
        if current_context.get("entities", {}).get("city"):
            result["entities"]["city"] = current_context["entities"]["city"]
        else:
            # Запрос на уточнение города
            result["intents"] = [{"name": "clarify_city_for_weather", "confidence": 0.95}]

    elif current_context.get("last_recognized_intent") == "clarify_city_for_weather":
        if result["entities"].get("city"):
            result["intents"] = [{"name": "get_weather", "confidence": 0.9}]
        else:
            result["intents"] = [{"name": "fallback_after_clarification_fail", "confidence": 1.0}]

    # --- Тематические фреймы (логика оставлена для совместимости) ---
    active_frames = []
    if is_get_weather_intent or current_context.get("last_recognized_intent") == "clarify_city_for_weather":
        weather_frame = {
            "name": "weather_inquiry_frame",
            "slots": {
                "city": result["entities"].get("city"),
                "date": result["entities"].get("date", "today")
            },
            "status": "incomplete"
        }
        if weather_frame["slots"]["city"]:
            weather_frame["status"] = "ready_to_fulfill"
        if current_context.get("last_recognized_intent") == "clarify_city_for_weather" and result["entities"].get("city"):
            weather_frame["status"] = "completed_after_clarification"
        active_frames.append(weather_frame)

    result["active_frames"] = active_frames

    # --- Логика Fallback ---
    # Если основной интент от OpenAI - это нечто неопределенное, можно выставить fallback
    if result["intents"][0]["name"] == "fallback_general":
        result["fallback_type"] = "general"

    return result
