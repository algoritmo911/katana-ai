# bot/nlp/context.py

def get_initial_context():
    """Возвращает начальный контекст для нового пользователя."""
    return {
        "last_recognized_intent": None,
        "last_processed_intent": None,
        "entities": {},
        "history": [] # history is now managed in katana_bot.py's user_memory
    }

def update_context(current_context: dict, nlp_result: dict, processed_intents_info: list) -> dict:
    """
    Обновляет контекст на основе результатов NLP-анализа и выполненных действий.
    Основная логика сохранения контекста сущностей теперь находится в parser.py.
    """
    new_context = current_context.copy()

    # 1. Update last recognized intent
    if nlp_result.get("intents"):
        new_context["last_recognized_intent"] = nlp_result["intents"][0]["name"]

    # 2. Update last processed intent
    main_processed_intent = next((p["name"] for p in processed_intents_info if p.get("processed")), None)
    if main_processed_intent:
        new_context["last_processed_intent"] = main_processed_intent

    # 3. Update entities from the final nlp_result
    # The parser has already handled merging entities from the previous context if it was a continuation.
    if nlp_result.get("entities"):
        new_context["entities"] = nlp_result["entities"]
    else:
        new_context["entities"] = {}

    return new_context
