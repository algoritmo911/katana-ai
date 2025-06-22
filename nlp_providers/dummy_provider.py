from nlp_providers.base import NLPProvider
import re

class DummyProvider(NLPProvider):
    """
    A dummy NLP provider for testing and demonstration purposes.
    It uses very simple keyword matching and regex for intents and slots.
    """

    def __init__(self, config: dict = None):
        """
        Initializes the DummyProvider.

        Args:
            config (dict, optional): Configuration specific to this provider.
                                     Example: {"mode": "test"}. Defaults to None.
        """
        self._name = "DummyProvider"
        self.config = config if config else {}
        # print(f"DummyProvider initialized with config: {self.config}") # For debugging

    @property
    def name(self) -> str:
        return self._name

    def get_intent(self, text: str) -> dict:
        text_lower = text.lower()

        # More specific intents first
        if "weather" in text_lower:
            return {"intent_name": "get_weather", "confidence": 0.9}
        elif "turn on" in text_lower and ("light" in text_lower or "lamp" in text_lower):
            return {"intent_name": "turn_on_light", "confidence": 0.85}
        elif "book" in text_lower and "flight" in text_lower:
            return {"intent_name": "book_flight", "confidence": 0.8}
        # General greeting check
        is_greeting = "hello" in text_lower or "hi" in text_lower
        contains_other_keywords = any(kw in text_lower for kw in ["weather", "light", "lamp", "flight", "book"])

        if is_greeting and not contains_other_keywords:
            return {"intent_name": "greeting", "confidence": 0.99}

        # If it's not a clear greeting or if other keywords dominated,
        # and it hasn't matched any specific intent above, it's unknown.
        return {"intent_name": "unknown_intent", "confidence": 0.5}

    def get_slots(self, text: str, intent: str = None) -> dict:
        slots = {}
        text_lower = text.lower()

        if intent == "get_weather":
            # Example: "weather in London", "weather for London"
            match = re.search(r"weather\s+(?:in|for)\s+([\w\s]+)", text_lower)
            if match:
                slots["location"] = match.group(1).strip().title()
            else: # Try to find location if "in" or "for" is not there, e.g. "London weather"
                match_general_location = re.search(r"([\w\s]+)\s+weather", text_lower)
                if match_general_location:
                    slots["location"] = match_general_location.group(1).strip().title()

        elif intent == "turn_on_light":
            # Regex to capture device name (potentially multi-word, including "light" or "lamp") and optional location
            # "turn on the [device_name] in the [location]"
            # "turn on the [device_name]"
            # "turn on [device_name]"
            match = re.search(r"turn on (?:the )?([\w\s]+? (?:light|lamp)|[\w\s]+)(?: in (?:the )?([\w\s]+))?$", text_lower)
            if match:
                device_name = match.group(1).strip()
                slots["device_name"] = device_name
                if match.group(2):
                    slots["location"] = match.group(2).strip()
            elif "light" in text_lower or "lamp" in text_lower: # Fallback for simple "turn on light"
                 slots["device_name"] = "default light"


        elif intent == "book_flight":
            # Try to find 'to [destination]'
            match_to = re.search(r"to\s+([\w\s]+?)(?:\s+from|\s+on|\s+for|$)", text_lower)
            if match_to:
                slots["destination"] = match_to.group(1).strip().title()

            # Try to find 'from [origin]'
            match_from = re.search(r"from\s+([\w\s]+?)(?:\s+to|\s+on|\s+for|$)", text_lower)
            if match_from:
                slots["origin"] = match_from.group(1).strip().title()

        # Generic: find numbers if any
        numbers = re.findall(r"\d+", text)
        if numbers:
            slots["numbers"] = [int(n) for n in numbers]

        return slots

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
    provider = DummyProvider()
    print(f"Testing provider: {provider.name}")

    test_phrases = [
        "Hello there!",
        "What's the weather like in Paris?",
        "turn on the living room lamp",
        "turn on kitchen light",
        "Book a flight to New York from London",
        "Book a flight from Berlin to Madrid",
        "Tell me a joke with number 42"
    ]

    for phrase in test_phrases:
        print(f"\nInput: {phrase}")
        # Test individual methods
        # intent = provider.get_intent(phrase)
        # print(f"  Intent: {intent}")
        # slots = provider.get_slots(phrase, intent.get("intent_name"))
        # print(f"  Slots: {slots}")

        # Test process method
        processed_output = provider.process(phrase)
        print(f"  Processed: {processed_output}")
