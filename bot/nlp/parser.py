# bot/nlp/parser.py
import re

# Простой список известных городов (можно расширить или использовать внешнюю библиотеку)
KNOWN_CITIES = ["москва", "питер", "санкт-петербург", "новосибирск", "екатеринбург", "казань", "нижний новгород", "челябинск", "омск", "самара", "ростов-на-дону", "уфа", "красноярск", "пермь", "воронеж", "волгоград", "лондон"] # Добавил Лондон для теста

def analyze_text(text, current_context):
    """
    Анализирует текст пользователя, определяет намерения и извлекает сущности.
    Это базовая реализация с использованием ключевых слов и регулярных выражений.
    """
    text_lower = text.lower()
    intents = []
    entities = {}

    # --- Распознавание намерений (очень упрощенно) ---
    if "погод" in text_lower or "прогноз" in text_lower:
        intents.append({"name": "get_weather", "confidence": 0.9})
    if "анекдот" in text_lower or "шутк" in text_lower or "рассмеши" in text_lower:
        intents.append({"name": "tell_joke", "confidence": 0.9})
    if "факт" in text_lower or "знаешь ли ты" in text_lower:
        intents.append({"name": "get_fact", "confidence": 0.8})
    if any(greet in text_lower for greet in ["привет", "здравствуй", "добрый день", "доброе утро", "добрый вечер"]):
        intents.append({"name": "greeting", "confidence": 0.95})
    if any(bye in text_lower for bye in ["пока", "до свидания", "всего доброго"]):
        intents.append({"name": "goodbye", "confidence": 0.95})
    if "который час" in text_lower or "сколько времени" in text_lower:
        intents.append({"name": "get_time", "confidence": 0.9})


    # --- Извлечение сущностей (улучшенное) ---
    # Города (для погоды)
    # Ищем явное указание города с предлогами или известные города без предлогов.
    city_pattern_preposition = r"(?:в|во|городе)\s+([А-Яа-яЁёГорода-]+)"
    city_matches_preposition = re.finditer(city_pattern_preposition, text, re.IGNORECASE)

    found_cities = []
    for match in city_matches_preposition:
        city_name = match.group(1)
        if city_name: # city_name.lower() in KNOWN_CITIES: # Можно добавить проверку на известный город, если нужно строже
            found_cities.append(city_name.capitalize())
            break # Берем первый найденный с предлогом

    if not found_cities:
        # Если с предлогом не нашли, ищем просто известные города в тексте
        # (это может дать ложные срабатывания на словах типа "привет", если "Привет" есть в KNOWN_CITIES, но наш список городов специфичнее)
        # Составляем паттерн для поиска любого из известных городов как отдельного слова
        # Добавим \b для границ слова, чтобы "Москвариум" не стал "Москва"
        known_cities_pattern = r"\b(" + "|".join(re.escape(city) for city in KNOWN_CITIES) + r")\b"
        city_matches_known = re.finditer(known_cities_pattern, text, re.IGNORECASE)
        for match in city_matches_known:
            city_name = match.group(1)
            if city_name:
                found_cities.append(city_name.capitalize())
                break # Берем первый найденный известный город


    if found_cities:
        entities["city"] = found_cities[0]

    # --- Логика контекста и уточнения ---
    is_get_weather_intent = any(intent["name"] == "get_weather" for intent in intents)

    if is_get_weather_intent and not entities.get("city"):
        # Если спрашивают погоду, но город не указан, проверяем контекст
        # Убрал проверку current_context.get("last_recognized_intent") == "get_weather", т.к. это может быть не всегда так,
        # если пользователь ответил на другой вопрос перед этим, но город в контексте остался.
        if current_context.get("entities", {}).get("city"):
            entities["city"] = current_context["entities"]["city"]
        else:
            # Запрос на уточнение города
            # Удаляем get_weather, если город не ясен, и добавляем clarify_city
            intents = [i for i in intents if i["name"] != "get_weather"]
            # Добавляем clarify_city_for_weather только если его еще нет (чтобы не дублировать)
            if not any(i["name"] == "clarify_city_for_weather" for i in intents):
                intents.append({"name": "clarify_city_for_weather", "confidence": 0.95})

    # Если текущий контекст ожидает уточнения города (т.е. предыдущий распознанный интент был clarify_city_for_weather),
    # и пользователь что-то ответил, и мы смогли извлечь город из этого ответа.
    elif current_context.get("last_recognized_intent") == "clarify_city_for_weather":
        if entities.get("city"): # Если в новом сообщении мы нашли город
            # Восстанавливаем намерение узнать погоду
            # Удаляем clarify_city_for_weather, если он был, и добавляем get_weather
            intents = [i for i in intents if i["name"] != "clarify_city_for_weather"]
            if not any(i["name"] == "get_weather" for i in intents): # Не дублировать
                intents.append({"name": "get_weather", "confidence": 0.85})
        else: # Город все еще не ясен после попытки уточнения
            intents = [i for i in intents if i["name"] != "clarify_city_for_weather"] # Удаляем старое уточнение
            if not any(i["name"] == "fallback_after_clarification_fail" for i in intents):
                 intents.append({"name": "fallback_after_clarification_fail", "confidence": 1.0})


    # --- Тематические фреймы (начальная реализация) ---
    active_frames = []
    # Пример: фрейм для погоды
    # TODO: Развивать логику фреймов, их активации и обновления на основе контекста
    if is_get_weather_intent or current_context.get("last_recognized_intent") == "clarify_city_for_weather":
        weather_frame = {
            "name": "weather_inquiry_frame",
            "slots": {
                "city": entities.get("city"),
                "date": entities.get("date", "today") # Пример, date не извлекается пока
            },
            "status": "incomplete" # Статус будет обновляться далее или в response_generator
        }
        if weather_frame["slots"]["city"]:
            weather_frame["status"] = "ready_to_fulfill" # Если есть город, можно пробовать выполнить

        # Если предыдущий интент был уточнение, а теперь есть город, то фрейм 'complete'
        if current_context.get("last_recognized_intent") == "clarify_city_for_weather" and entities.get("city"):
            weather_frame["status"] = "completed_after_clarification"

        active_frames.append(weather_frame)

    # --- Логика Fallback (улучшенная) ---
    fallback_type = None
    if not intents: # Если вообще никаких интентов не нашлось
        # Проверяем, есть ли сущности, чтобы предложить уточняющий fallback
        if entities:
            intents.append({"name": "fallback_clarification_needed", "confidence": 0.7})
            fallback_type = "clarification_needed"
        else:
            intents.append({"name": "fallback_general", "confidence": 1.0})
            fallback_type = "general"

    # Если интенты есть, но это только clarify_city_for_weather и город всё ещё неясен
    # (это состояние должно было привести к fallback_after_clarification_fail ранее, но как доп. проверка)
    # Эта логика должна применяться только если clarify_city_for_weather НЕ был только что добавлен
    # в результате get_weather без города.
    # Вместо этого, такая проверка уже есть выше в блоке:
    # elif current_context.get("last_recognized_intent") == "clarify_city_for_weather":
    #     if entities.get("city"): ...
    #     else: intents.append({"name": "fallback_after_clarification_fail", ...})
    # Поэтому этот блок ниже можно упростить или удалить, если он дублирует.
    # Пока что закомментируем его, чтобы восстановить правильную логику clarify_city_for_weather.

    # is_clarify_only_without_city = len(intents) == 1 and \
    #                                intents[0]["name"] == "clarify_city_for_weather" and \
    #                                not entities.get("city") and \
    #                                current_context.get("last_recognized_intent") == "clarify_city_for_weather" # Добавлено условие на предыдущий контекст
    # if is_clarify_only_without_city:
    #     # Переопределяем на fallback_after_clarification_fail если он еще не там
    #     if not any(i["name"] == "fallback_after_clarification_fail" for i in intents):
    #         intents = [i for i in intents if i["name"] != "clarify_city_for_weather"]
    #         intents.append({"name": "fallback_after_clarification_fail", "confidence": 1.0})
    #         fallback_type = "clarification_failed"


    # Сортировка намерений по уверенности (важно для выбора основного намерения)
    intents.sort(key=lambda x: x["confidence"], reverse=True)

    # Убедимся, что если есть clarify_city_for_weather, то get_weather удален, если город не определен
    # Эта логика уже есть выше, но можно сделать финальную проверку
    has_clarify_intent = any(i["name"] == "clarify_city_for_weather" for i in intents)
    if has_clarify_intent and not entities.get("city"):
        intents = [i for i in intents if i["name"] != "get_weather"]
        # Если clarify_city_for_weather остался единственным и без города,
        # это должно было быть обработано как fallback_after_clarification_fail или clarify_city_for_weather
        # Логика выше должна это покрывать.

    # Если после всех манипуляций список интентов пуст (маловероятно), добавляем общий fallback
    if not intents:
        intents.append({"name": "fallback_general", "confidence": 1.0})
        if not fallback_type: fallback_type = "general"

    # Если есть интенты, но нет fallback_type, а первый интент - это один из fallback'ов, установим тип
    if intents and not fallback_type:
        if intents[0]["name"] == "fallback_general": fallback_type = "general"
        elif intents[0]["name"] == "fallback_clarification_needed": fallback_type = "clarification_needed"
        elif intents[0]["name"] == "fallback_after_clarification_fail": fallback_type = "clarification_failed"


    return {
        "text": text,
        "intents": intents,
        "entities": entities,
        "active_frames": active_frames,
        "fallback_type": fallback_type
    }
