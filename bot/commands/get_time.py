# bot/commands/get_time.py
from datetime import datetime
from . import register_command

@register_command("get_time", metadata={"description": "Сообщает текущее время."})
def handle_intent_get_time(chat_id, entities, current_context):
    """Обработчик для намерения 'get_time'."""
    now = datetime.now()
    return f"Текущее время: {now.strftime('%H:%M:%S')}."