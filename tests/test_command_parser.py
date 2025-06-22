import unittest
from unittest.mock import MagicMock, patch
from parser.command_parser import CommandParser
from nlp_providers.base import NLPProvider
from nlp_providers.dummy_provider import DummyProvider # For concrete instance if needed

class TestCommandParser(unittest.TestCase):

    def test_init_with_provider_instance(self):
        """Test initialization with a direct NLPProvider instance."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "MockProvider"
        parser = CommandParser(nlp_provider=mock_provider)
        self.assertIs(parser.nlp_provider, mock_provider)

    @patch('parser.command_parser.get_active_nlp_provider')
    def test_init_loads_from_config(self, mock_get_provider):
        """Test initialization loads provider from config if none is passed."""
        mock_configured_provider = MagicMock(spec=NLPProvider)
        mock_configured_provider.name = "ConfiguredProvider"
        mock_get_provider.return_value = mock_configured_provider

        parser = CommandParser()
        self.assertIs(parser.nlp_provider, mock_configured_provider)
        mock_get_provider.assert_called_once()

    @patch('parser.command_parser.get_active_nlp_provider')
    def test_init_handles_config_load_failure(self, mock_get_provider):
        """Test initialization handles failure to load provider from config."""
        mock_get_provider.side_effect = ValueError("Config load error")

        # Check if a warning is printed (optional, depends on logging setup)
        # For now, just ensure nlp_provider is None and no crash
        with patch('builtins.print') as mock_print: # to suppress print output during test
            parser = CommandParser()
            self.assertIsNone(parser.nlp_provider)
            # Check if the warning message was part of the print call
            # self.assertTrue(any("Warning: Could not load NLP provider from config" in call_args[0][0] for call_args in mock_print.call_args_list))


    def test_parse_with_mock_provider_process(self):
        """Test parse method using provider's process method."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "TestProcessProvider"
        expected_intent = {"intent_name": "test_intent", "confidence": 0.9}
        expected_slots = {"slot1": "value1"}
        mock_provider.process.return_value = {
            "intent": expected_intent,
            "slots": expected_slots
        }
        # Ensure get_intent and get_slots are NOT called if process is used
        mock_provider.get_intent = MagicMock()
        mock_provider.get_slots = MagicMock()

        parser = CommandParser(nlp_provider=mock_provider)
        text = "some input text"
        result = parser.parse(text)

        mock_provider.process.assert_called_once_with(text)
        mock_provider.get_intent.assert_not_called()
        mock_provider.get_slots.assert_not_called()

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intent"], expected_intent)
        self.assertEqual(result["slots"], expected_slots)
        self.assertEqual(result["provider"], "TestProcessProvider")

    def test_parse_with_mock_provider_fallback(self):
        """Test parse method falling back to get_intent/get_slots if process raises NotImplementedError."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "TestFallbackProvider"
        mock_provider.process.side_effect = NotImplementedError # Simulate process not being implemented

        expected_intent = {"intent_name": "fallback_intent", "confidence": 0.8}
        expected_slots = {"location": "home"}
        mock_provider.get_intent.return_value = expected_intent
        mock_provider.get_slots.return_value = expected_slots

        parser = CommandParser(nlp_provider=mock_provider)
        text = "another input"
        result = parser.parse(text)

        mock_provider.process.assert_called_once_with(text)
        mock_provider.get_intent.assert_called_once_with(text)
        mock_provider.get_slots.assert_called_once_with(text, "fallback_intent")

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intent"], expected_intent)
        self.assertEqual(result["slots"], expected_slots)
        self.assertEqual(result["provider"], "TestFallbackProvider")

    def test_parse_with_no_provider(self):
        """Test parse method when no NLP provider is available."""
        # Simulate provider loading failure
        with patch('parser.command_parser.get_active_nlp_provider', side_effect=ValueError("Failed to load")):
            with patch('builtins.print') as mock_print: # Suppress warning
                parser = CommandParser()

        text = "input with no provider"
        result = parser.parse(text)

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intent"]["name"], "error_no_provider")
        self.assertIn("NLP provider not available", result["slots"]["message"])
        self.assertNotIn("provider", result) # Provider name should not be in result

    def test_parse_with_provider_exception(self):
        """Test parse method when provider's process method raises an exception."""
        mock_provider = MagicMock(spec=NLPProvider)
        mock_provider.name = "ErrorProneProvider"
        error_message = "NLP service unavailable"
        mock_provider.process.side_effect = Exception(error_message)

        parser = CommandParser(nlp_provider=mock_provider)
        text = "trigger error"

        with patch('builtins.print') as mock_print: # Suppress error print
            result = parser.parse(text)

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intent"]["name"], "error_provider_failure")
        self.assertEqual(result["slots"]["message"], error_message)
        self.assertNotIn("provider", result) # Provider name should not be in result if it failed

    def test_parse_with_dummy_provider(self):
        """Integration test of CommandParser with the actual DummyProvider."""
        # This requires DummyProvider to be correctly implemented.
        # And settings.yaml should point to it, or we instantiate it directly.

        # To make this test independent of settings.yaml, instantiate DummyProvider directly.
        # Or, ensure test_settings.yaml points to DummyProvider and use CommandParser()

        dummy_config = {"mode": "test_from_command_parser"}
        dummy_provider_instance = DummyProvider(config=dummy_config)
        parser = CommandParser(nlp_provider=dummy_provider_instance)

        text = "hello world"
        result = parser.parse(text)

        self.assertEqual(result["text"], text)
        self.assertEqual(result["intent"]["intent_name"], "greeting")
        self.assertEqual(result["provider"], "DummyProvider")
        # DummyProvider's get_slots for "greeting" might be empty or have specific behavior
        # self.assertEqual(result["slots"], {}) # Adjust based on DummyProvider's logic

        text_weather = "weather in Neverland"
        result_weather = parser.parse(text_weather)
        self.assertEqual(result_weather["intent"]["intent_name"], "get_weather")
        self.assertEqual(result_weather["slots"].get("location"), "Neverland")


if __name__ == '__main__':
    unittest.main()
