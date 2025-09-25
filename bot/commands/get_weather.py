# bot/commands/get_weather.py
from . import register_command

@register_command("get_weather", metadata={"description": "Сообщает погоду в указанном городе."})
def handle_intent_get_weather(chat_id, entities, current_context):
    """Обработчик для намерения 'get_weather'."""
    city = entities.get("city")
    if city:
        return f"☀️ Погода в городе {city} отличная! (но это не точно)"
    else:
        # Эта логика теперь управляется NLP-парсером, который должен был создать интент 'clarify_city_for_weather'
        return "Хм, кажется, я должен был спросить город, но что-то пошло не так."

@register_command("clarify_city_for_weather", metadata={"description": "Запрашивает уточнение города для прогноза погоды."})
def handle_intent_clarify_city_for_weather(chat_id, entities, current_context):
    """Обработчик для запроса уточнения города."""
    return "Для какого города вы хотите узнать погоду?"