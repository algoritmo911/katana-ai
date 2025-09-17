import functools
import json
from .nlp_processor import NLPProcessor, NLPError

class Parser:
    """
    Адаптер, который преобразует "сырой" результат от NLPProcessor
    в структурированный формат, ожидаемый логикой бота.
    Не несет ответственности за управление состоянием.
    """
    def __init__(self, nlp_processor: NLPProcessor):
        self.nlp_processor = nlp_processor
        self._intent_map = {
            "запрос информации": "get_fact",
            "социальный диалог": "greeting",
            "уточнение": "clarification",
            "recall_information": "recall_information",
            "search_documents": "search_documents"
        }

    def _adapt_intent(self, raw_intent: str, original_text: str) -> str:
        """Адаптирует и нормализует намерение."""
        if "погод" in original_text.lower() or "прогноз" in original_text.lower():
            return "get_weather"
        return self._intent_map.get(raw_intent, raw_intent)

    def _adapt_entities(self, raw_entities: list) -> dict:
        """Адаптирует список сущностей в словарь."""
        entities = {}
        for entity in raw_entities:
            entity_type = entity.get("type", "").lower()
            entity_text = entity.get("text")
            if entity_type and entity_text:
                if entity_type in ["location", "loc"]:
                    entities["city"] = entity_text
                else:
                    entities[entity_type] = entity_text
        return entities

    def analyze_text(self, text: str, history: list = None) -> dict:
        """
        Анализирует текст пользователя, вызывая NLPProcessor и адаптируя его ответ.
        """
        dialogue_history_for_prompt = []
        if history:
            for entry in history[-5:]:
                dialogue_history_for_prompt.append({"role": "user", "content": entry.get("user")})
                if entry.get("bot"):
                    dialogue_history_for_prompt.append({"role": "assistant", "content": entry.get("bot")})

        history_json = json.dumps(dialogue_history_for_prompt)

        try:
            nlp_data = self.nlp_processor.process_text(text, dialogue_history_json=history_json)
        except NLPError as e:
            print(f"NLP ERROR: {e}")
            return {
                "text": text, "intents": [{"name": "fallback_general", "confidence": 1.0}], "entities": {},
                "active_frames": [], "fallback_type": "general", "error": str(e)
            }

        intent_name = self._adapt_intent(nlp_data.get("intent", "fallback_general"), text)
        entities = self._adapt_entities(nlp_data.get("entities", []))

        result = {
            "text": text,
            "intents": [{"name": intent_name, "confidence": 0.95}],
            "entities": entities,
            "active_frames": [], # Placeholder for future frame logic
            "fallback_type": "fallback_general" if intent_name == "fallback_general" else None,
            "metadata": {"raw_openai_response": nlp_data}
        }
        return result
