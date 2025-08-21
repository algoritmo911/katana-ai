class KatanaAgent:
    def __init__(self):
        pass

    def get_response(self, text: str, current_chat_history: list) -> str:
        """
        A mock response generator for the KatanaAgent.
        """
        return f"This is a mock response to: {text}"
