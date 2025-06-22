from abc import abstractmethod
from typing import List, Dict, Any, Optional
from nlp_providers.base import NLPProvider

class AdvancedNLPProvider(NLPProvider):
    """
    Abstract Base Class for advanced NLP providers that support
    multi-intent recognition, context management, and richer responses.
    """

    @abstractmethod
    def process_advanced(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes the input text, optionally using context, to get potentially
        multiple intents, slots, and any other provider-specific information.

        Args:
            text: The user's input string.
            context: (Optional) A dictionary containing contextual information from
                     the dialogue, user state, or previous turns. The structure of
                     this context is flexible and may be defined by the application
                     or specific providers. Example:
                     {
                         "user_id": "some_user_id",
                         "previous_intent": "ask_weather",
                         "active_slots": {"location": "London"},
                         "dialogue_history": [
                             {"speaker": "user", "text": "What's the weather like?"},
                             {"speaker": "bot", "text": "In which city?"},
                             {"speaker": "user", "text": "London"}
                         ]
                     }

        Returns:
            A dictionary containing comprehensive NLP results. Example:
            {
                "intents": [
                    {"intent_name": "book_flight", "confidence": 0.88, "provider_details": {...}},
                    {"intent_name": "request_info", "confidence": 0.65, "provider_details": {...}}
                ],
                "slots": {
                    "destination": "London",
                    "departure_date": "2024-12-25",
                    "category": "business_class"
                },
                "raw_response": ..., # Provider's original response, if useful
                "processed_text": "...", # Text after any provider preprocessing
                "language": "en" # Detected language
            }
            If no primary intent is found, "intents" list might be empty or contain a
            fallback intent like "unknown_intent".
        """
        pass

    # We can choose to override or rely on the base NLPProvider's
    # get_intent, get_slots, and process methods.
    # For an AdvancedNLPProvider, it's likely that `process_advanced`
    # would be the primary method used, and the others could either:
    # 1. Be adapted to use `process_advanced` internally.
    # 2. Be marked as less relevant or raise NotImplementedError if not sensible.

    # Example of adapting `process` from base class:
    def process(self, text: str) -> dict:
        """
        Basic processing, potentially calling process_advanced without context
        and adapting its output to the simpler format.
        """
        advanced_result = self.process_advanced(text, context=None)

        # Adapt to the simpler format expected by the base `process` method
        # This adaptation might take the top intent, for example.
        primary_intent = {}
        if advanced_result.get("intents"):
            primary_intent = advanced_result["intents"][0] # Take the first one as primary

        return {
            "intent": {
                "intent_name": primary_intent.get("intent_name", "unknown_intent"),
                "confidence": primary_intent.get("confidence", 0.0)
            },
            "slots": advanced_result.get("slots", {})
        }

    # get_intent and get_slots could be similarly adapted or deemed less critical
    # if the application primarily uses process_advanced.

    def get_intent(self, text: str) -> dict:
        """
        Gets the primary intent, possibly by calling process_advanced.
        """
        advanced_result = self.process_advanced(text, context=None)
        if advanced_result.get("intents"):
            top_intent = advanced_result["intents"][0]
            return {
                "intent_name": top_intent.get("intent_name", "unknown_intent"),
                "confidence": top_intent.get("confidence", 0.0)
            }
        return {"intent_name": "unknown_intent", "confidence": 0.0}

    def get_slots(self, text: str, intent: str = None) -> dict:
        """
        Gets slots, possibly by calling process_advanced.
        The 'intent' argument might be less relevant if process_advanced handles it.
        """
        # Context for process_advanced could potentially include the passed 'intent'
        # if the provider can use that hint.
        # context_hint = {"current_intent_hint": intent} if intent else None
        advanced_result = self.process_advanced(text, context=None) # Or with context_hint
        return advanced_result.get("slots", {})

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the NLP provider.
        (Inherited from NLPProvider, but must be implemented by concrete class)
        """
        pass
