from katana_single_app.services.nlp_service import Intent

async def handle_intent(intent: Intent) -> str:
    """
    Handles the recognized intent and returns an appropriate response.
    This is the core business logic handler.
    """
    if intent.name == 'status':
        return "Katana Core v15 is online..."
    elif intent.name == 'analyze':
        return "Analysis command received..."
    elif intent.name == 'think':
        return "Thinking command received..."
    elif intent.name == 'unknown':
        return "Unknown command..."

    # As a fallback, though the NLP service should always return one of the above.
    return "Command not recognized."
