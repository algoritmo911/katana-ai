import unittest
import os
from unittest.mock import patch, MagicMock

from nlp_providers.advanced_base import AdvancedNLPProvider
from nlp_providers.example_openai_provider import ExampleOpenAIProvider, MockOpenAIClient
# We need MockOpenAIClient to potentially mock its behavior further if needed, or inspect calls.

class TestExampleOpenAIProvider(unittest.TestCase):

    def setUp(self):
        self.base_config = {
            "api_key_env_var": "OPENAI_API_KEY", # Actual key not used due to mock
            "api_key": "mock_key_for_testing", # Simulate key being loaded
            "default_model": "mock-completion-model",
            "model_type": "completion",
            "timeout": 10,
            "generation_params": {"temperature": 0.5}
        }
        # Ensure a dummy env var is set if the provider tries to read it directly for some reason,
        # though our MockOpenAIClient doesn't strictly need it.
        os.environ["OPENAI_API_KEY"] = "dummy_env_key_for_openai_test"

    def test_initialization_completion_type(self):
        """Test provider initializes correctly for completion models."""
        config = self.base_config.copy()
        provider = ExampleOpenAIProvider(config=config)
        self.assertEqual(provider.name, "ExampleOpenAIProvider")
        self.assertEqual(provider.default_model, "mock-completion-model")
        self.assertEqual(provider.model_type, "completion")
        self.assertEqual(provider.api_key, "mock_key_for_testing")
        self.assertIsInstance(provider.client, MockOpenAIClient)

    def test_initialization_chat_type(self):
        """Test provider initializes correctly for chat models."""
        config = self.base_config.copy()
        config["default_model"] = "mock-chat-model"
        config["model_type"] = "chat"
        provider = ExampleOpenAIProvider(config=config)
        self.assertEqual(provider.default_model, "mock-chat-model")
        self.assertEqual(provider.model_type, "chat")

    @patch.object(MockOpenAIClient, 'completions')
    def test_process_advanced_completion_model(self, mock_completions_resource):
        """Test process_advanced with a completion model type using mock."""
        # Setup mock for completions.create()
        mock_create_fn = MagicMock()
        # This is the structure our MockOpenAIClient's completions().create() returns
        mock_create_fn.return_value = {
            "simulated_api_response": {"choices": [{"text": "Mocked completion output"}]},
            "derived_intents": [{"intent_name": "mock_completed_intent", "confidence": 0.92}],
            "derived_slots": {"completed_slot": "value_c"}
        }
        mock_completions_resource.return_value.create = mock_create_fn

        provider = ExampleOpenAIProvider(config=self.base_config)
        text = "Test completion input"
        context = {"user_id": "test_user_completion"}

        result = provider.process_advanced(text, context=context)

        mock_create_fn.assert_called_once()
        # Check some args of the call to mock_create_fn if necessary
        # args, kwargs = mock_create_fn.call_args
        # self.assertEqual(kwargs['model'], provider.default_model)

        self.assertIn("intents", result)
        self.assertEqual(result["intents"][0]["intent_name"], "mock_completed_intent")
        self.assertEqual(result["slots"]["completed_slot"], "value_c")
        self.assertIsNotNone(result.get("raw_response")) # Corrected key

    @patch.object(MockOpenAIClient, 'chat')
    def test_process_advanced_chat_model(self, mock_chat_resource):
        """Test process_advanced with a chat model type using mock."""
        mock_create_fn = MagicMock()
        mock_create_fn.return_value = {
            "simulated_api_response": {"choices": [{"message": {"content": "Mocked chat output"}}]},
            "derived_intents": [{"intent_name": "mock_chat_intent", "confidence": 0.95}],
            "derived_slots": {"chat_slot": "value_chat"}
        }
        mock_chat_resource.return_value.create = mock_create_fn

        chat_config = self.base_config.copy()
        chat_config["model_type"] = "chat"
        chat_config["default_model"] = "mock-chat-model-id"
        provider = ExampleOpenAIProvider(config=chat_config)

        text = "Test chat input"
        context = {"dialogue_history": [{"role": "user", "content": "Previous message"}]}

        result = provider.process_advanced(text, context=context)

        mock_create_fn.assert_called_once()
        # args, kwargs = mock_create_fn.call_args
        # self.assertEqual(kwargs['model'], provider.default_model)
        # self.assertIn({"role": "user", "content": text}, kwargs['messages'])

        self.assertEqual(result["intents"][0]["intent_name"], "mock_chat_intent")
        self.assertEqual(result["slots"]["chat_slot"], "value_chat")

    def test_base_nlp_methods_adaptation(self):
        """Test that base NLPProvider methods are adapted from process_advanced."""
        # The mock client inside ExampleOpenAIProvider already returns some derived intents/slots
        # We rely on that for this test of the adapter methods in AdvancedNLPProvider (implemented by ExampleOpenAIProvider)
        provider = ExampleOpenAIProvider(config=self.base_config)
        test_text = "What is the weather in a mocked city?" # Mock should find 'get_weather'

        # Test get_intent
        intent_result = provider.get_intent(test_text)
        self.assertIsInstance(intent_result, dict)
        self.assertEqual(intent_result.get("intent_name"), "get_weather") # Based on MockOpenAIClient's logic
        self.assertGreater(intent_result.get("confidence"), 0)

        # Test get_slots
        slots_result = provider.get_slots(test_text)
        self.assertIsInstance(slots_result, dict)
        # Based on MockOpenAIClient's logic for "weather in X"
        self.assertIn("location", slots_result)
        self.assertEqual(slots_result.get("location"), "a mocked city")


        # Test process
        process_result = provider.process(test_text)
        self.assertIsInstance(process_result, dict)
        self.assertEqual(process_result.get("intent", {}).get("intent_name"), "get_weather")
        self.assertEqual(process_result.get("slots", {}).get("location"), "a mocked city")

    def test_process_advanced_api_error_simulation(self):
        """Test error handling when the (mocked) API call fails."""
        # Configure the mock to raise an exception
        with patch.object(MockOpenAIClient, 'completions') as mock_completions_resource:
            mock_create_fn = MagicMock(side_effect=Exception("Mock API Network Error"))
            mock_completions_resource.return_value.create = mock_create_fn

            provider = ExampleOpenAIProvider(config=self.base_config)
            result = provider.process_advanced("trigger error", context=None)

            self.assertIn("intents", result)
            self.assertEqual(result["intents"][0]["intent_name"], "provider_error")
            self.assertIn("Mock API Network Error", result["intents"][0].get("details", ""))

if __name__ == '__main__':
    unittest.main()
