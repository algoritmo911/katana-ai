# bot/commands/greetings.py
import random
from . import register_command

@register_command("greeting", metadata={"description": "Отвечает на приветствие."})
def handle_intent_greeting(chat_id, entities, current_context):
    """Обработчик для намерения 'greeting'."""
    return random.choice(["Привет!", "Здравствуйте!", "Рад вас снова видеть!"])

@register_command("goodbye", metadata={"description": "Отвечает на прощание."})
def handle_intent_goodbye(chat_id, entities, current_context):
    """Обработчик для намерения 'goodbye'."""
    return random.choice(["Пока!", "До свидания!", "Надеюсь, скоро увидимся."])