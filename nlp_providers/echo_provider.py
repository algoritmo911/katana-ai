from nlp_providers.base import NLPProvider

class EchoProvider(NLPProvider):
    """
    An NLP provider that simply echoes back the input text in slots
    and returns a fixed intent. Useful for basic testing of the pipeline.
    """

    def __init__(self, config: dict = None):
        """
        Initializes the EchoProvider.

        Args:
            config (dict, optional): Configuration specific to this provider.
                                     Example: {"prefix": "Echo: "}. Defaults to None.
        """
        self._name = "EchoProvider"
        self.config = config if config else {}
        self.prefix = self.config.get("prefix", "") # Get prefix from config or default to empty
        # print(f"EchoProvider initialized with config: {self.config}, prefix: '{self.prefix}'") # For debugging


    @property
    def name(self) -> str:
        return self._name

    def get_intent(self, text: str) -> dict:
        """
        Returns a fixed intent indicating the text was echoed.
        """
        return {"intent_name": "echo", "confidence": 1.0}

    def get_slots(self, text: str, intent: str = None) -> dict:
        """
        Returns the original text as a slot.
        """
        return {"echoed_text": f"{self.prefix}{text}"}

    def process(self, text: str) -> dict:
        """
        Processes the input text to get both intent and slots.
        """
        intent_data = self.get_intent(text)
        slots_data = self.get_slots(text, intent_data.get("intent_name"))

        return {
            "intent": intent_data,
            "slots": slots_data
        }

if __name__ == '__main__':
    # Example Usage
    # With default config
    provider_default = EchoProvider()
    print(f"Testing provider: {provider_default.name} (default config)")
    test_phrase = "This is a test message."
    processed_default = provider_default.process(test_phrase)
    print(f"Input: {test_phrase}\nProcessed: {processed_default}")

    # With custom config
    custom_config = {"prefix": "Said: "}
    provider_custom = EchoProvider(config=custom_config)
    print(f"\nTesting provider: {provider_custom.name} (custom config)")
    processed_custom = provider_custom.process(test_phrase)
    print(f"Input: {test_phrase}\nProcessed: {processed_custom}")
