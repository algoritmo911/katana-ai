# bot/commands/tell_joke.py
import random
from . import register_command

@register_command("tell_joke", metadata={"description": "Рассказывает случайный анекдот."})
def handle_intent_tell_joke(chat_id, entities, current_context):
    """Обработчик для намерения 'tell_joke'."""
    jokes = [
        "Колобок повесился.",
        "Почему программисты предпочитают темную тему? Потому что свет притягивает баги!",
        "Заходит улитка в бар..."
    ]
    return random.choice(jokes)