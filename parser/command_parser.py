import re
from typing import Optional, Dict, Any
from nlp_providers.base import NLPProvider
from config.loader import get_active_nlp_provider

class CommandParser:
    """
    Parses user input to identify intents and extract slots using an NLP provider.
    """
    def __init__(self, nlp_provider: Optional[NLPProvider] = None):
        """
        Initializes the CommandParser.

        Args:
            nlp_provider: An instance of NLPProvider. If None, it will try
                          to load the active provider from the configuration.
        """
        if nlp_provider:
            self.nlp_provider = nlp_provider
        else:
            try:
                self.nlp_provider = get_active_nlp_provider()
            except Exception as e:
                print(f"Warning: Could not load NLP provider from config: {e}. Using a fallback mechanism or provider might be unavailable.")
                # As a fallback, one might instantiate a very basic default provider here,
                # or ensure that methods handle self.nlp_provider being None.
                # For now, we'll let it be None and handle it in parse method.
                self.nlp_provider = None

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parses the input text to extract intent and slots.

        Args:
            text: The user's input string.

        Returns:
            A dictionary containing the intent and slots, e.g.,
            {
                "text": "show me flights to London",
                "intent": {"name": "find_flight", "confidence": 0.9},
                "slots": {"destination": "London"}
            }
            If the provider is not available or fails, it might return a default
            response indicating an error or inability to parse.
        """
        if not self.nlp_provider:
            return {
                "text": text,
                "intent": {"name": "error_no_provider", "confidence": 1.0},
                "slots": {"message": "NLP provider not available."}
            }

        try:
            # Use the provider's process method if available and efficient
            processed_data = self.nlp_provider.process(text)
            intent_data = processed_data.get("intent", {"name": "unknown_intent", "confidence": 0.0})
            slots_data = processed_data.get("slots", {})

        except NotImplementedError:
            # Fallback if process is not implemented or preferred to be separate
            intent_data = self.nlp_provider.get_intent(text)
            slots_data = self.nlp_provider.get_slots(text, intent_data.get("intent_name")) # Use "intent_name"
        except Exception as e:
            print(f"Error during NLP processing with {self.nlp_provider.name}: {e}")
            return {
                "text": text,
                "intent": {"name": "error_provider_failure", "confidence": 1.0},
                "slots": {"message": str(e)}
            }

        return {
            "text": text,
            "intent": intent_data,
            "slots": slots_data,
            "provider": self.nlp_provider.name
        }

    # Basic keyword/regex based intent and slot extraction (can be a fallback or simple default)
    # This part is more for a scenario where no sophisticated NLP provider is used,
    # or as an example for a very simple provider.
    # For this project, we assume the NLPProvider handles this logic.
    # However, I'll leave a placeholder structure for such basic parsing if needed directly in the parser
    # for some reason, though it's better delegated to a provider.

    def _simple_parse_intent(self, text: str) -> Dict[str, Any]:
        """A very basic intent parser, keyword-based."""
        text_lower = text.lower()
        if "hello" in text_lower or "hi" in text_lower:
            return {"name": "greeting", "confidence": 0.9}
        if "weather" in text_lower:
            return {"name": "get_weather", "confidence": 0.8}
        if "turn on" in text_lower and "light" in text_lower:
            return {"name": "turn_on_light", "confidence": 0.85}
        return {"name": "unknown", "confidence": 0.5}

    def _simple_extract_slots(self, text: str, intent_name: Optional[str] = None) -> Dict[str, Any]:
        """A very basic slot extractor, regex/keyword-based."""
        slots = {}
        text_lower = text.lower()
        if intent_name == "get_weather":
            # Example: "weather in London"
            match = re.search(r"weather in ([\w\s]+)", text_lower)
            if match:
                slots["location"] = match.group(1).strip()

        if intent_name == "turn_on_light":
            # Example: "turn on the kitchen light"
            match = re.search(r"turn on the ([\w\s]+) light", text_lower)
            if match:
                slots["light_name"] = match.group(1).strip()
            elif "light" in text_lower: # "turn on light"
                 slots["light_name"] = "default"


        # Generic slot: extract numbers
        numbers = re.findall(r"\d+", text)
        if numbers:
            slots["numbers"] = [int(n) for n in numbers]

        return slots

# Example Usage (will require dummy providers to be implemented for full functionality)
if __name__ == '__main__':
    # This example will print a warning because DummyProvider is not yet implemented.
    # Once DummyProvider (or another provider set in settings.yaml) is available,
    # this will work as intended.

    print("Initializing CommandParser...")
    parser = CommandParser() # Will try to load from config

    if parser.nlp_provider:
        print(f"CommandParser initialized with NLP provider: {parser.nlp_provider.name}")

        test_phrases = [
            "Hello there!",
            "What's the weather like in Paris?",
            "Turn on the living room lamp",
            "Book a flight to New York"
        ]

        for phrase in test_phrases:
            print(f"\nParsing: '{phrase}'")
            result = parser.parse(phrase)
            print(f"Result: {result}")
    else:
        print("CommandParser initialized without a functional NLP provider.")
        print("Using internal simple parser as a demonstration (not part of the main flow):")

        # Demonstrate the _simple_parse_intent and _simple_extract_slots
        # Note: These methods are not directly used by parser.parse() when an NLPProvider is configured.
        # They are internal helper methods that *could* be used by a very basic NLPProvider.

        test_phrases_simple = [
            "hello",
            "what is the weather in London",
            "turn on the kitchen light",
            "some other command"
        ]
        for phrase in test_phrases_simple:
            intent = parser._simple_parse_intent(phrase)
            slots = parser._simple_extract_slots(phrase, intent.get("name"))
            print(f"\nText: {phrase}")
            print(f"  Simple Intent: {intent}")
            print(f"  Simple Slots: {slots}")
