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


    # --- Логика Fallback ---
    if not intents: # Если вообще никаких интентов не нашлось
        intents.append({"name": "fallback", "confidence": 1.0})
    # Если интенты есть, но среди них нет get_weather, а clarify_city_for_weather остался (маловероятно после логики выше, но как подстраховка)
    elif not any(i["name"] == "get_weather" for i in intents) and any(i["name"] == "clarify_city_for_weather" for i in intents) and not entities.get("city"):
         # Если у нас только clarify_city_for_weather, но города нет, это странно, должен быть fallback
         pass # Логика выше должна была это покрыть, оставив clarify_city_for_weather или заменив на fallback_after_clarification_fail


    # Сортировка намерений по уверенности (важно для выбора основного намерения)
    intents.sort(key=lambda x: x["confidence"], reverse=True)

    # Убедимся, что если есть clarify_city_for_weather, то get_weather удален, если город не определен
    has_clarify = any(i["name"] == "clarify_city_for_weather" for i in intents)
    if has_clarify and not entities.get("city"):
        intents = [i for i in intents if i["name"] != "get_weather"]
        # Если после удаления get_weather и при наличии clarify_city остался только он, а других интентов нет, то все ок.
        # Если были другие интенты, они остаются.
        # Если clarify_city - единственный интент, это нормально.

    # Если после всех манипуляций список интентов пуст (маловероятно), добавляем fallback
    if not intents:
        intents.append({"name": "fallback", "confidence": 1.0})


    return {
        "text": text,
        "intents": intents,
        "entities": entities,
    }
