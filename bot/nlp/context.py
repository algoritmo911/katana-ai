# bot/nlp/context.py

def update_context(current_context, nlp_result, processed_intents_info):
    """
    Обновляет контекст на основе результатов NLP-анализа и выполненных действий.
    """
    new_context = current_context.copy()

    # 1. Обновляем last_recognized_intent из nlp_result (берем первое, т.к. они отсортированы по confidence)
    if nlp_result.get("intents") and nlp_result["intents"][0]:
        new_context["last_recognized_intent"] = nlp_result["intents"][0]["name"]
    else:
        # Если NLP не вернул интентов (что маловероятно, т.к. должен быть fallback),
        # не меняем last_recognized_intent или сбрасываем его. Пока оставим как есть.
        pass

    # 2. Обновляем last_processed_intent на основе того, что реально было обработано
    # Берем первое успешно обработанное намерение из списка handler_info
    # (предполагается, что в processed_intents_info порядок соответствует порядку обработки или приоритету)
    main_processed_intent = None
    for handler_info in processed_intents_info:
        if handler_info.get("processed"):
            main_processed_intent = handler_info["name"]
            break
    if main_processed_intent:
        new_context["last_processed_intent"] = main_processed_intent
    # Если ничего не было обработано (например, все хендлеры вернули ошибку или не нашлись),
    # то last_processed_intent не обновляется или можно его сбросить.
    # Пока оставляем как есть: если ничего не обработано, он не изменится с предыдущего шага.

    # 3. Обновляем сущности
    # Сначала очистим сущности, если текущее распознанное намерение не предполагает их использование из прошлого.
    # Это очень упрощенная логика. В идеале нужно знать, какие сущности релевантны для каких интентов.
    # Например, если новый интент - "расскажи анекдот", старый город из "погоды" уже не нужен.

    # Определяем, нужно ли очищать предыдущие сущности.
    # Мы очищаем сущности, если текущий главный обработанный интент
    # не является продолжением предыдущего контекста (например, уточнение).
    # Это помогает избежать "залипания" старых сущностей.

    previous_intent = current_context.get("last_processed_intent")
    current_main_intent = new_context.get("last_processed_intent") # Уже обновлен выше

    # Список интентов, которые обычно являются частью последовательности и сохраняют контекст
    STICKY_INTENT_PAIRS = {
        # предыдущий интент: [список последующих интентов, которые продолжают контекст]
        "get_weather": ["clarify_city_for_weather"], # Если спросили погоду, а потом уточняют город
        "clarify_city_for_weather": ["get_weather"], # Если спросили город, а потом дают город для погоды
        # Можно добавить другие пары, например, для многошаговых диалогов
    }

    # Категории интентов (упрощенно)
    INTENT_CATEGORIES = {
        "get_weather": "task",
        "clarify_city_for_weather": "task_clarification",
        "get_time": "task",
        "tell_joke": "chitchat",
        "get_fact": "chitchat",
        "greeting": "chitchat",
        "goodbye": "chitchat",
        "fallback": "system",
        "fallback_after_clarification_fail": "system"
    }

    # Получаем категории предыдущего и текущего интентов
    prev_category = INTENT_CATEGORIES.get(previous_intent, "unknown")
    current_category = INTENT_CATEGORIES.get(current_main_intent, "unknown")

    should_clear_entities = True
    if previous_intent and current_main_intent:
        # Не очищаем, если это "липкая" пара
        if previous_intent in STICKY_INTENT_PAIRS and \
           current_main_intent in STICKY_INTENT_PAIRS[previous_intent]:
            should_clear_entities = False
        # Не очищаем, если категория та же и это не chitchat (chitchat каждый раз новый)
        # и не системный (fallback)
        elif prev_category == current_category and \
             prev_category not in ["chitchat", "system", "unknown", "task_clarification"]:
            should_clear_entities = False
        # Если предыдущий был уточнением, а текущий - задача (например, clarify_city -> get_weather)
        elif prev_category == "task_clarification" and current_category == "task":
             # Здесь мы уже проверили STICKY_INTENT_PAIRS, так что если это не та пара, то чистим
             # Однако, если clarify_city_for_weather -> get_weather, то это уже обработано STICKY_INTENT_PAIRS
             # Это условие на случай, если есть другие task_clarification -> task, не указанные в STICKY_INTENT_PAIRS,
             # но для них мы пока что будем очищать сущности, если они не "липкие".
             # По сути, если мы дошли сюда, и предыдущий был task_clarification, а текущий task,
             # и они не в STICKY_INTENT_PAIRS, то лучше очистить.
             pass # should_clear_entities остается True

    if should_clear_entities:
        # print(f"DEBUG: Clearing entities. Prev: {previous_intent}, Curr: {current_main_intent}")
        new_context["entities"] = {}
    # else:
        # print(f"DEBUG: NOT clearing entities. Prev: {previous_intent}, Curr: {current_main_intent}")


    # Теперь добавляем/обновляем сущности из текущего nlp_result
    if nlp_result.get("entities"):
        new_context["entities"].update(nlp_result.get("entities", {}))


    # Синхронизация last_recognized_intent если clarify_city_for_weather успешно привел к get_weather
    # Эта логика уже была, но теперь она работает с потенциально очищенными/обновленными new_context["entities"]
    if new_context.get("last_processed_intent") == "get_weather" and \
       current_context.get("last_recognized_intent") == "clarify_city_for_weather" and \
       new_context["entities"].get("city"): # Убедимся что город есть ПОСЛЕ обновления сущностей
        new_context["last_recognized_intent"] = "get_weather"

    return new_context
