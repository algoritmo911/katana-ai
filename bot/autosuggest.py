# bot/autosuggest.py
import random

def get_suggestions(context, history):
    """
    Analyzes the user's conversation history and the current context to predict
    the next likely command or intent.

    :param context: The current dialogue context.
    :param history: The user's conversation history.
    :return: A list of suggested commands or intents.
    """
    suggestions = []
    last_intent = context.get("last_processed_intent")

    # --- Context-specific suggestions ---
    if last_intent == "get_weather":
        # If the last intent was about weather, suggest related actions.
        suggestions.append({"text": "Узнать погоду в другом городе?", "callback_data": "suggest_weather_new_city"})
        suggestions.append({"text": "Спросить что-нибудь еще?", "callback_data": "suggest_anything_else"})

    elif last_intent == "tell_joke":
        # If the user just heard a joke, they might want another one.
        suggestions.append({"text": "Рассказать еще один анекдот?", "callback_data": "suggest_joke"})
        suggestions.append({"text": "Узнать интересный факт?", "callback_data": "suggest_fact"})

    elif last_intent == "get_fact":
        # If the user just learned a fact, they might want another one.
        suggestions.append({"text": "Рассказать еще один факт?", "callback_data": "suggest_fact"})
        suggestions.append({"text": "Рассказать анекдот?", "callback_data": "suggest_joke"})

    elif last_intent == "clarify_city_for_weather":
        # If the bot asked for a city, the user might be stuck.
        suggestions.append({"text": "Например, 'погода в Лондоне'", "callback_data": "suggest_weather_london"})
        suggestions.append({"text": "Отменить запрос погоды", "callback_data": "suggest_cancel_weather"})

    # --- Generic suggestions for when the user is idle ---
    # These will be added if no specific suggestions were generated.
    if not suggestions:
        generic_suggestions = [
            {"text": "Какая погода?", "callback_data": "suggest_weather"},
            {"text": "Расскажи анекдот", "callback_data": "suggest_joke"},
            {"text": "Какой сегодня день?", "callback_data": "suggest_get_time"}, # Assumes get_time intent exists
            {"text": "Удиви меня фактом", "callback_data": "suggest_fact"},
        ]
        # Add a random selection of generic suggestions to avoid being repetitive.
        # Ensure we don't add duplicates if some were already added.
        existing_callbacks = {s["callback_data"] for s in suggestions}
        for gs in random.sample(generic_suggestions, k=min(len(generic_suggestions), 2)): # Pick 2 random suggestions
             if gs["callback_data"] not in existing_callbacks:
                suggestions.append(gs)

    # --- Fallback suggestion ---
    # If after all logic there are still no suggestions, add a generic help prompt.
    if not suggestions:
        suggestions.append({"text": "Чем я могу помочь?", "callback_data": "suggest_help"})

    return suggestions
