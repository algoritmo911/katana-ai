# bot/commands/fallbacks.py
import random
from . import register_command

@register_command("fallback_general", metadata={"description": "Общий ответ, когда команда не распознана."})
def handle_intent_fallback_general(chat_id, entities, current_context):
    """Обработчик для общего fallback."""
    options = [
        "Я не совсем понял, что вы имеете в виду. Можете переформулировать?",
        "Хм, я пока не умею на это отвечать. Попробуйте что-нибудь другое.",
        "Извините, я не распознал вашу команду. Может, попробуем что-то из этого: погода, факт, анекдот?"
    ]
    return random.choice(options)

@register_command("fallback_clarification_needed", metadata={"description": "Ответ, когда для выполнения команды нужны уточнения."})
def handle_intent_fallback_clarification_needed(chat_id, entities, current_context):
    """Обработчик для fallback, когда нужны уточнения."""
    recognized_entities_parts = []
    if entities.get("city"):
        recognized_entities_parts.append(f"город {entities['city']}")
    # Можно добавить другие сущности по мере их появления

    if recognized_entities_parts:
        return f"Я понял, что речь идет о {', '.join(recognized_entities_parts)}, но не совсем ясно, что вы хотите. Можете уточнить?"
    else:
        # Если сущностей нет, но этот fallback вызван, это странно, но дадим общий ответ.
        return "Мне кажется, я уловил часть информации, но не могу понять запрос целиком. Пожалуйста, уточните."

@register_command("fallback_after_clarification_fail", metadata={"description": "Ответ, когда уточнение не удалось."})
def handle_intent_fallback_after_clarification_fail(chat_id, entities, current_context):
    """Обработчик для fallback после неудачного уточнения."""
    return "Я все еще не понял, какой город вас интересует. Давайте попробуем другую команду?"