# bot/nlp/context.py

def get_initial_context():
    """Возвращает начальный контекст для нового пользователя."""
    return {
        "last_recognized_intent": None, # Основное распознанное намерение из NLP
        "last_processed_intent": None, # Основное фактически обработанное намерение
        "entities": {},
        "history_summary": None,
    }

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
    if new_context.get("last_recognized_intent") not in ["get_weather", "clarify_city_for_weather"] and \
       new_context.get("last_processed_intent") not in ["get_weather", "clarify_city_for_weather"]:
        if "city" in new_context["entities"]: # Очищаем город, если он не относится к погоде
            del new_context["entities"]["city"]

    # Теперь добавляем/обновляем сущности из текущего nlp_result
    if nlp_result.get("entities"):
        new_context["entities"].update(nlp_result.get("entities", {}))

    # Если было уточнение clarify_city_for_weather и оно привело к get_weather,
    # и город теперь есть в сущностях, то last_recognized_intent должен стать get_weather.
    # Это должно было произойти еще на этапе nlp_parser.
    # Здесь мы просто убеждаемся, что контекст это отражает.
    if new_context.get("last_processed_intent") == "get_weather" and \
       current_context.get("last_recognized_intent") == "clarify_city_for_weather" and \
       new_context["entities"].get("city"):
        new_context["last_recognized_intent"] = "get_weather" # Синхронизируем

    return new_context
