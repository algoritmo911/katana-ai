class DialogueContextManager:
    """
    Управляет состоянием диалога для каждой сессии.
    """
    def get_initial_session(self):
        """Возвращает начальную структуру сессии."""
        return {
            "context": {
                "last_intent": None,
                "entities": {},
            },
            "history": []
        }

    def update_context(self, current_context: dict, nlp_result: dict) -> dict:
        """
        Обновляет контекст диалога на основе нового NLP-результата.
        Эта функция теперь является центром управления состоянием.
        """
        new_context = current_context.copy()

        # 1. Обновляем последний интент
        new_intent = nlp_result.get("intents", [{}])[0].get("name")
        if new_intent:
            new_context["last_intent"] = new_intent

        # 2. Управляем сущностями на основе состояния диалога
        raw_nlp_response = nlp_result.get("metadata", {}).get("raw_openai_response", {})
        dialogue_state = raw_nlp_response.get("dialogue_state")

        new_entities = nlp_result.get("entities", {})

        if dialogue_state == 'continuation':
            # Если это продолжение диалога, объединяем сущности.
            # Новые сущности имеют приоритет над старыми.
            merged_entities = {**current_context.get("entities", {}), **new_entities}
            new_context["entities"] = merged_entities
        else:
            # Если это новый запрос, полностью заменяем сущности.
            new_context["entities"] = new_entities

        return new_context
