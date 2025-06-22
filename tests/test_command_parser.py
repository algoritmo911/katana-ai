import unittest
from unittest.mock import MagicMock, patch
from parser.command_parser import CommandParser, DEFAULT_FALLBACK_MESSAGE, UNKNOWN_INTENT_THRESHOLD
from nlp_providers.base import NLPProvider
from nlp_providers.advanced_base import AdvancedNLPProvider # For type hinting and mocking
from nlp_providers.dummy_provider import DummyProvider
from nlp_providers.example_openai_provider import ExampleOpenAIProvider # For concrete advanced provider

class TestCommandParser(unittest.TestCase):

    def test_init_with_provider_instance_and_context(self):
        """Test initialization with a direct NLPProvider instance and initial context."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "MockProvider"
        initial_context = {"user_id": "test_user_123"}
        parser = CommandParser(nlp_provider=mock_provider, dialogue_context=initial_context)
        self.assertIs(parser.nlp_provider, mock_provider)
        self.assertEqual(parser.dialogue_context["user_id"], "test_user_123")

    @patch('parser.command_parser.get_active_nlp_provider')
    def test_init_loads_from_config_default_context(self, mock_get_provider):
        """Test initialization loads provider from config and uses default context if none passed."""
        mock_configured_provider = MagicMock(spec=NLPProvider)
        mock_configured_provider.name = "ConfiguredProvider"
        mock_get_provider.return_value = mock_configured_provider

        parser = CommandParser()
        self.assertIs(parser.nlp_provider, mock_configured_provider)
        mock_get_provider.assert_called_once()
        self.assertIn("session_id", parser.dialogue_context) # Check for default context key

    @patch('parser.command_parser.get_active_nlp_provider')
    def test_init_handles_config_load_failure(self, mock_get_provider):
        """Test initialization handles failure to load provider from config."""
        mock_get_provider.side_effect = ValueError("Config load error")
        with patch('builtins.print') as mock_print:
            parser = CommandParser()
            self.assertIsNone(parser.nlp_provider)
            # Check if the warning message was part of the print call
            self.assertTrue(any("Warning: Could not load NLP provider" in call_args[0][0] for call_args in mock_print.call_args_list))

    def test_parse_with_basic_provider(self):
        """Test parse method using a basic NLPProvider (mocked)."""
        mock_provider = MagicMock(spec=NLPProvider) # Not AdvancedNLPProvider
        mock_provider.name = "BasicMockProvider"
        expected_intent_data = {"intent_name": "basic_intent", "confidence": 0.9}
        expected_slots_data = {"basic_slot": "basic_value"}

        # Mock get_intent and get_slots as these would be called for non-AdvancedNLPProvider
        mock_provider.get_intent.return_value = expected_intent_data
        mock_provider.get_slots.return_value = expected_slots_data

        parser = CommandParser(nlp_provider=mock_provider)
        text = "input for basic provider"
        result = parser.parse(text)

        mock_provider.get_intent.assert_called_once_with(text)
        mock_provider.get_slots.assert_called_once_with(text, "basic_intent")

        self.assertEqual(result["text"], text)
        self.assertEqual(len(result["intents"]), 1)
        self.assertEqual(result["intents"][0], expected_intent_data)
        self.assertEqual(result["slots"], expected_slots_data)
        self.assertEqual(result["provider"], "BasicMockProvider")
        self.assertIsNone(result.get("fallback_response")) # Assuming good confidence

    def test_parse_with_advanced_provider(self):
        """Test parse method using an AdvancedNLPProvider (mocked)."""
        mock_advanced_provider = MagicMock(spec=AdvancedNLPProvider)
        mock_advanced_provider.name = "AdvancedMockProvider"

        adv_response = {
            "intents": [{"intent_name": "adv_intent_1", "confidence": 0.95}, {"intent_name": "adv_intent_2", "confidence": 0.7}],
            "slots": {"adv_slot": "adv_value"},
            "raw_response": {"detail": "raw_adv_data"}, # Corrected key
            "processed_text": "processed advanced input",
            "language": "fr"
        }
        mock_advanced_provider.process_advanced.return_value = adv_response

        parser = CommandParser(nlp_provider=mock_advanced_provider)
        text = "input for advanced provider"
        initial_context = {"session_id": "adv_session"}
        parser.dialogue_context = initial_context.copy() # Set initial context for the parser instance

        result = parser.parse(text, context_override={"temp_key": "temp_val"})

        # process_advanced should be called with merged context
        expected_call_context = initial_context.copy()
        expected_call_context.update({"temp_key": "temp_val"})
        mock_advanced_provider.process_advanced.assert_called_once_with(text, context=expected_call_context)

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intents"], adv_response["intents"])
        self.assertEqual(result["slots"], adv_response["slots"])
        self.assertEqual(result["raw_response"], adv_response["raw_response"]) # Corrected assertion key
        self.assertEqual(result["processed_text"], adv_response["processed_text"])
        self.assertEqual(result["language"], adv_response["language"])
        self.assertEqual(result["provider"], "AdvancedMockProvider")

    def test_fallback_response_unknown_intent(self):
        """Test fallback response for unknown intent."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "FallbackTestProvider"
        mock_provider.get_intent.return_value = {"intent_name": "unknown_intent", "confidence": 0.3}
        mock_provider.get_slots.return_value = {}

        parser = CommandParser(nlp_provider=mock_provider)
        result = parser.parse("some gibberish text")

        self.assertEqual(result["fallback_response"], DEFAULT_FALLBACK_MESSAGE)
        self.assertEqual(result["intents"][0]["intent_name"], "unknown_intent")

    def test_fallback_response_low_confidence(self):
        """Test fallback response for low confidence intent."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "LowConfidenceProvider"
        # Confidence is below UNKNOWN_INTENT_THRESHOLD (0.4 by default)
        mock_provider.get_intent.return_value = {"intent_name": "get_info", "confidence": UNKNOWN_INTENT_THRESHOLD - 0.1}
        mock_provider.get_slots.return_value = {"topic": "something"}

        parser = CommandParser(nlp_provider=mock_provider)
        result = parser.parse("tell me about something vaguely")

        self.assertEqual(result["fallback_response"], DEFAULT_FALLBACK_MESSAGE)
        self.assertEqual(result["intents"][0]["intent_name"], "get_info")


    def test_no_fallback_if_confidence_is_good(self):
        """Test no fallback response if confidence is sufficient."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "GoodConfidenceProvider"
        mock_provider.get_intent.return_value = {"intent_name": "get_info", "confidence": UNKNOWN_INTENT_THRESHOLD + 0.1}
        mock_provider.get_slots.return_value = {}

        parser = CommandParser(nlp_provider=mock_provider)
        result = parser.parse("tell me about something clearly")

        self.assertIsNone(result["fallback_response"])

    def test_dialogue_context_update(self):
        """Test that dialogue context is updated after a successful parse."""
        mock_provider = MagicMock(spec=AdvancedNLPProvider)
        mock_provider.name = "ContextUpdateProvider"
        adv_response = {
            "intents": [{"intent_name": "order_pizza", "confidence": 0.9, "details":{}}],
            "slots": {"size": "large", "topping": "pepperoni"},
        }
        mock_provider.process_advanced.return_value = adv_response

        parser = CommandParser(nlp_provider=mock_provider)
        self.assertEqual(len(parser.dialogue_context["previous_intents"]), 0)
        self.assertEqual(parser.dialogue_context["active_slots"], {})

        parser.parse("I want a large pepperoni pizza")

        self.assertEqual(len(parser.dialogue_context["previous_intents"]), 1)
        self.assertEqual(parser.dialogue_context["previous_intents"][0]["name"], "order_pizza")
        self.assertEqual(parser.dialogue_context["previous_intents"][0]["slots"], {"size": "large", "topping": "pepperoni"})
        self.assertEqual(parser.dialogue_context["active_slots"], {"size": "large", "topping": "pepperoni"})

        # Second parse, check context accumulation (simple merge for slots)
        adv_response_2 = {
            "intents": [{"intent_name": "add_drink", "confidence": 0.88, "details":{}}],
            "slots": {"drink": "coke"}, # New slot
        }
        mock_provider.process_advanced.return_value = adv_response_2
        parser.parse("and a coke")

        self.assertEqual(len(parser.dialogue_context["previous_intents"]), 2)
        self.assertEqual(parser.dialogue_context["previous_intents"][1]["name"], "add_drink")
        self.assertEqual(parser.dialogue_context["active_slots"], {"size": "large", "topping": "pepperoni", "drink": "coke"})


    def test_parse_with_no_provider_returns_error_intent(self):
        """Test parse method when no NLP provider is available, ensuring specific error intent."""
        with patch('parser.command_parser.get_active_nlp_provider', side_effect=ValueError("Failed to load")):
            with patch('builtins.print'): # Suppress warning
                parser = CommandParser()

        text = "input with no provider"
        result = parser.parse(text)

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intents"][0]["intent_name"], "error_no_provider")
        self.assertIn("NLP provider not available.", result["slots"]["message"])
        self.assertIsNotNone(result["fallback_response"])


    def test_parse_with_provider_exception_returns_error_intent(self):
        """Test parse method when provider raises an exception."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "ErrorProneProvider"
        error_message = "NLP service unavailable"
        # Simulate error from basic provider path
        mock_provider.get_intent.side_effect = Exception(error_message)

        parser = CommandParser(nlp_provider=mock_provider)
        text = "trigger error"

        with patch('builtins.print'): # Suppress error print
            result = parser.parse(text)

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intents"][0]["intent_name"], "error_provider_failure")
        self.assertEqual(result["intents"][0]["details"], error_message)
        self.assertIsNotNone(result["fallback_response"])

    # Conceptual test for katana bridge placeholder
    def test_conceptual_katana_bridge_formatting(self):
        parser = CommandParser(nlp_provider=MagicMock(spec=NLPProvider)) # Basic provider

        # Scenario 1: Fallback
        fallback_result = {"fallback_response": "Sorry, say again." , "intents":[]}
        katana_action_fallback = parser._prepare_for_katana_bridge(fallback_result)
        self.assertEqual(katana_action_fallback["action"], "inform_user")
        self.assertEqual(katana_action_fallback["message"], "Sorry, say again.")

        # Scenario 2: Mapped Intent
        mapped_intent_result = {
            "intents": [{"intent_name": "get_weather", "confidence": 0.9}],
            "slots": {"location": "moon"}
        }
        katana_action_mapped = parser._prepare_for_katana_bridge(mapped_intent_result)
        self.assertEqual(katana_action_mapped["action"], "fetch_weather_data")
        self.assertEqual(katana_action_mapped["parameters"], {"location": "moon"})

        # Scenario 3: Unmapped but valid Intent
        unmapped_intent_result = {
            "intents": [{"intent_name": "some_other_valid_intent", "confidence": 0.9}],
            "slots": {}
        }
        katana_action_unmapped = parser._prepare_for_katana_bridge(unmapped_intent_result)
        self.assertEqual(katana_action_unmapped["action"], "clarify")


if __name__ == '__main__':
    unittest.main()
