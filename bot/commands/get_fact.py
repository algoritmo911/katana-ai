# bot/commands/get_fact.py
import random
from . import register_command

@register_command("get_fact", metadata={"description": "Рассказывает случайный факт."})
def handle_intent_get_fact(chat_id, entities, current_context):
    """Обработчик для намерения 'get_fact'."""
    facts = [
        "Медведи могут лазить по деревьям.",
        "Самый долгий полет курицы — 13 секунд.",
        "У улитки около 25 000 зубов."
    ]
    return random.choice(facts)