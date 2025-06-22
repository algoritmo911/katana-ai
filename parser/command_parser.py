import re
from typing import Optional, Dict, Any, List # Added List
from nlp_providers.base import NLPProvider
from nlp_providers.advanced_base import AdvancedNLPProvider # Import AdvancedNLPProvider
from config.loader import get_active_nlp_provider

# Configuration for fallback messages and confidence thresholds
DEFAULT_FALLBACK_MESSAGE = "Sorry, I didn't quite understand that. Could you please rephrase?"
UNKNOWN_INTENT_THRESHOLD = 0.4 # Example threshold for considering an intent too uncertain

class CommandParser:
    """
    Parses user input to identify intents (potentially multiple) and extract slots,
    using a configured NLP provider. Handles dialogue context and provides fallbacks.
    """
    def __init__(self, nlp_provider: Optional[NLPProvider] = None, dialogue_context: Optional[Dict[str, Any]] = None):
        """
        Initializes the CommandParser.

        Args:
            nlp_provider: An instance of NLPProvider or AdvancedNLPProvider.
                          If None, it will try to load from configuration.
            dialogue_context: Initial dialogue context.
        """
        if nlp_provider:
            self.nlp_provider = nlp_provider
        else:
            try:
                self.nlp_provider = get_active_nlp_provider()
            except Exception as e:
                print(f"Warning: Could not load NLP provider from config: {e}. Parser might not function correctly.")
                self.nlp_provider = None

        self.dialogue_context = dialogue_context if dialogue_context else self._get_default_dialogue_context()
        # self.dialogue_history = [] # Could be part of dialogue_context

    def _get_default_dialogue_context(self) -> Dict[str, Any]:
        return {
            "session_id": "default_session", # Example context item
            "previous_intents": [],
            "active_slots": {},
            "user_preferences": {} # Example
        }

    def update_dialogue_context(self, new_data: Dict[str, Any]):
        """Updates the internal dialogue context."""
        # Simple merge, could be more sophisticated
        for key, value in new_data.items():
            if isinstance(self.dialogue_context.get(key), list) and isinstance(value, list):
                self.dialogue_context[key].extend(value) # Merge lists
                # Limit history size if it's a list of previous intents/turns
                if key == "previous_intents" and len(self.dialogue_context[key]) > 5: # Keep last 5
                    self.dialogue_context[key] = self.dialogue_context[key][-5:]
            elif isinstance(self.dialogue_context.get(key), dict) and isinstance(value, dict):
                self.dialogue_context[key].update(value) # Merge dicts (slots, preferences)
            else:
                self.dialogue_context[key] = value


    def parse(self, text: str, context_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parses the input text to extract intents and slots, using dialogue context.

        Args:
            text: The user's input string.
            context_override: Optional dictionary to temporarily override or add to the
                              current dialogue context for this specific parse operation.

        Returns:
            A dictionary containing the parsing result, e.g.,
            {
                "text": "show me flights to London",
                "intents": [{"name": "find_flight", "confidence": 0.9, ...}, ...], // List of intents
                "slots": {"destination": "London", ...},
                "provider": "ProviderName",
                "raw_provider_response": {...}, // Optional raw response
                "processed_text": "...", // Optional text after provider preprocessing
                "language": "en", // Optional detected language
                "fallback_response": "Optional message if intent is unclear"
            }
        """
        current_parse_context = self.dialogue_context.copy()
        if context_override:
            current_parse_context.update(context_override) # Allow temporary overrides

        if not self.nlp_provider:
            return {
                "text": text,
                "intents": [{"intent_name": "error_no_provider", "confidence": 1.0}],
                "slots": {"message": "NLP provider not available."},
                "fallback_response": "I'm currently unable to process requests."
            }

        parsed_result = {
            "text": text,
            "intents": [],
            "slots": {},
            "provider": self.nlp_provider.name,
            "fallback_response": None
        }

        try:
            if isinstance(self.nlp_provider, AdvancedNLPProvider):
                # Use process_advanced if available, passing current_parse_context
                adv_result = self.nlp_provider.process_advanced(text, context=current_parse_context)
                parsed_result["intents"] = adv_result.get("intents", [])
                parsed_result["slots"] = adv_result.get("slots", {})
                parsed_result["raw_response"] = adv_result.get("raw_response") # Corrected key for assignment
                parsed_result["processed_text"] = adv_result.get("processed_text", text)
                parsed_result["language"] = adv_result.get("language")
            else:
                # Fallback to basic provider methods
                # This part adapts the simpler NLPProvider output to the new structure
                intent_data = self.nlp_provider.get_intent(text)
                slots_data = self.nlp_provider.get_slots(text, intent_data.get("intent_name"))
                # Wrap in a list to match the multi-intent structure
                parsed_result["intents"] = [intent_data] if intent_data else []
                parsed_result["slots"] = slots_data
                # No raw_response, processed_text, language from basic provider by default

            # Fallback logic
            primary_intent_name = None
            primary_intent_confidence = 0.0
            if parsed_result["intents"]:
                # Assuming intents are sorted by confidence or the first is primary
                primary_intent_name = parsed_result["intents"][0].get("intent_name", "unknown_intent")
                primary_intent_confidence = parsed_result["intents"][0].get("confidence", 0.0)

            if not parsed_result["intents"] or \
               primary_intent_name == "unknown_intent" or \
               primary_intent_name == "fallback_intent" or \
               primary_intent_confidence < UNKNOWN_INTENT_THRESHOLD:
                parsed_result["fallback_response"] = DEFAULT_FALLBACK_MESSAGE
                # Ensure there's at least a fallback intent if list is empty
                if not parsed_result["intents"]:
                    parsed_result["intents"] = [{"intent_name": "fallback_intent", "confidence": 1.0, "details": "No intent recognized."}]


            # Update dialogue context (example: add current primary intent to history)
            # More sophisticated context updates would happen here or in a DialogueManager
            if primary_intent_name and primary_intent_name not in ["unknown_intent", "fallback_intent", "error_no_provider", "error_provider_failure"]:
                self.update_dialogue_context({
                    "previous_intents": [{"name": primary_intent_name, "slots": parsed_result["slots"].copy()}],
                    "active_slots": {**self.dialogue_context.get("active_slots",{}), **parsed_result["slots"]} # Merge slots
                })

            # Placeholder for katana_agent_bridge integration
            # parsed_result["katana_action"] = self._prepare_for_katana_bridge(parsed_result)

        except Exception as e:
            print(f"Error during NLP processing with {self.nlp_provider.name}: {e}")
            import traceback
            print(traceback.format_exc()) # Print full traceback for debugging
            parsed_result["intents"] = [{"intent_name": "error_provider_failure", "confidence": 1.0, "details": str(e)}]
            parsed_result["slots"] = {"message": str(e)}
            parsed_result["fallback_response"] = "Sorry, I encountered an error trying to understand that."

        return parsed_result

    def _prepare_for_katana_bridge(self, parsed_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Conceptual: Formats the parsed result for katana_agent_bridge.
        The actual format depends on katana_agent_bridge's expected input.
        """
        if parsed_result.get("fallback_response"):
            return {"action": "inform_user", "message": parsed_result["fallback_response"]}

        if parsed_result["intents"]:
            primary_intent = parsed_result["intents"][0] # Assuming first is primary
            # This is highly dependent on how katana_agent_bridge maps intents to actions
            action_map = {
                "get_weather": "fetch_weather_data",
                "turn_on_light": "control_smart_home_device",
                "book_flight": "initiate_flight_booking_flow"
                # ... more mappings
            }
            action_name = action_map.get(primary_intent.get("intent_name"))
            if action_name:
                return {
                    "action": action_name,
                    "parameters": parsed_result.get("slots", {}),
                    "intent_details": primary_intent # Pass along full intent info if needed
                }
        return {"action": "clarify", "message": "I'm not sure what action to take for that."}


# Example Usage
if __name__ == '__main__':
    print("Initializing CommandParser...")
    # To test with ExampleOpenAIProvider, you would set it as active in settings.yaml
    # and ensure OPENAI_API_KEY (or other relevant keys) are in the environment.
    # For now, it will likely use DummyProvider by default from settings.yaml.

    # os.environ["OPENAI_API_KEY"] = "YOUR_KEY_HERE" # Example if testing OpenAI directly

    parser = CommandParser()

    if parser.nlp_provider:
        print(f"CommandParser initialized with NLP provider: {parser.nlp_provider.name}")
        print(f"Initial dialogue context: {parser.dialogue_context}")

        test_scenarios = [
            {"text": "Hello there!", "context": None},
            {"text": "What's the weather like in Paris?", "context": None},
            {"text": "and in Berlin?", "context": {"previous_intents": [{"name": "get_weather", "slots": {"location": "Paris"}}]}}, # Example context
            {"text": "Turn on the living room lamp", "context": None},
            {"text": "Book a flight to New York", "context": None},
            {"text": "gibberish askdjhaskd", "context": None} # Test fallback
        ]

        for scenario in test_scenarios:
            print(f"\nParsing: '{scenario['text']}' with context: {scenario['context']}")
            # Pass context_override to the parse method for this specific call
            result = parser.parse(scenario['text'], context_override=scenario.get('context'))

            print(f"Result: Intents: {result.get('intents')}, Slots: {result.get('slots')}")
            if result.get('fallback_response'):
                print(f"  Fallback: {result['fallback_response']}")
            if isinstance(parser.nlp_provider, AdvancedNLPProvider):
                 print(f"  Raw Response: {result.get('raw_provider_response') is not None}") # just show if it exists

            # Conceptual call to katana bridge preparation
            # katana_payload = parser._prepare_for_katana_bridge(result)
            # print(f"  Katana Payload (Conceptual): {katana_payload}")
            print(f"Updated dialogue context after parse: {parser.dialogue_context}")


    else:
        print("CommandParser initialized without a functional NLP provider.")
