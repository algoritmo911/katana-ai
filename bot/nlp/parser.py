import functools
from .nlp_processor import NLPProcessor, NLPError

@functools.lru_cache(maxsize=1)
def get_nlp_processor():
    """Initializes and returns a singleton instance of NLPProcessor."""
    try:
        return NLPProcessor()
    except ValueError as e:
        print(f"CRITICAL ERROR: Failed to initialize NLPProcessor. {e}")
        return None

def analyze_text(text: str, current_context: dict, history: list = None) -> dict:
    """
    Analyzes user text using NLPProcessor, including dialogue history for context.
    """
    nlp_processor = get_nlp_processor()
    if not nlp_processor:
        return {
            "text": text, "intents": [{"name": "fallback_general", "confidence": 1.0}], "entities": {},
            "active_frames": [], "fallback_type": "general", "error": "NLP processor is not available."
        }

    # Format the history for the OpenAI prompt
    dialogue_history_for_prompt = []
    if history:
        for entry in history[-5:]: # Use last 5 turns for context
            dialogue_history_for_prompt.append({"role": "user", "content": entry.get("user")})
            if entry.get("bot"):
                dialogue_history_for_prompt.append({"role": "assistant", "content": entry.get("bot")})

    try:
        nlp_data = nlp_processor.process_text(text, dialogue_history=dialogue_history_for_prompt)
    except NLPError as e:
        print(f"NLP ERROR: {e}")
        return {
            "text": text, "intents": [{"name": "fallback_general", "confidence": 1.0}], "entities": {},
            "active_frames": [], "fallback_type": "general", "error": str(e)
        }

    # Adapt the OpenAI output to the bot's expected structure
    raw_intent = nlp_data.get("intent", "fallback_general")
    intent_map = {
        "запрос информации": "get_fact", "социальный диалог": "greeting",
        "уточнение": "clarification", "recall_information": "recall_information",
        "search_documents": "search_documents"
    }
    intent_name = intent_map.get(raw_intent, raw_intent)
    if "погод" in text.lower() or "прогноз" in text.lower():
        intent_name = "get_weather"
    intents = [{"name": intent_name, "confidence": 0.95}]

    entities = {}
    for entity in nlp_data.get("entities", []):
        entity_type, entity_text = entity.get("type", "").lower(), entity.get("text")
        if entity_type and entity_text:
            if entity_type in ["location", "loc"]:
                entities["city"] = entity_text
            else:
                entities[entity_type] = entity_text

    # Update context based on dialogue state
    dialogue_state = nlp_data.get("dialogue_state")
    if dialogue_state == 'continuation' and current_context.get('entities'):
        # If it's a continuation, merge old entities with new ones, prioritizing new ones.
        merged_entities = {**current_context['entities'], **entities}
        entities = merged_entities

    result = {
        "text": text, "intents": intents, "entities": entities,
        "active_frames": [], "fallback_type": "fallback_general" if intent_name == "fallback_general" else None,
        "metadata": {"raw_openai_response": nlp_data}
    }
    return result
