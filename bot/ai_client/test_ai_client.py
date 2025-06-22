import unittest
from unittest.mock import patch, MagicMock, call
import logging

# Suppress logger output during tests unless specifically testing logging
logging.getLogger('bot.ai_client.ai_client').setLevel(logging.CRITICAL)
logging.getLogger('bot.ai_client.key_manager').setLevel(logging.CRITICAL) # Also for KeyManager if AIClient instantiates it

# Ensure modules can be found (similar to test_key_manager.py)
import sys
from pathlib import Path
module_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(module_dir))

from ai_client import AIClient, SUPPORTED_PROVIDERS, DEFAULT_KEYS_FILE
from key_manager import ApiKey # Needed for mock return values

# Use a different dummy file for AIClient tests if it creates one, to avoid conflict
AI_CLIENT_TEST_KEYS_FILE = "ai_client_test_keys.json"

class TestAIClient(unittest.TestCase):

    def setUp(self):
        # We will mock KeyManager directly, so no actual file needed for most tests
        # However, AIClient's __init__ might try to create KeyManager.
        # We can patch KeyManager's __init__ or the whole class.
        self.mock_key_manager_instance = MagicMock()

        # Patch KeyManager class. When AIClient calls KeyManager(), it gets our mock_key_manager_instance
        self.key_manager_patcher = patch('ai_client.KeyManager', return_value=self.mock_key_manager_instance)
        self.mock_key_manager_class = self.key_manager_patcher.start()

        self.ai_client = AIClient(keys_filepath=AI_CLIENT_TEST_KEYS_FILE) # Path won't be used by mock

    def tearDown(self):
        self.key_manager_patcher.stop()
        # Clean up any dummy file AIClient might have created if not fully mocked for file ops
        if AI_CLIENT_TEST_KEYS_FILE != DEFAULT_KEYS_FILE and os.path.exists(AI_CLIENT_TEST_KEYS_FILE):
            # Check if it's an empty JSON object, indicating it was auto-created by KeyManager (if not mocked early enough)
            try:
                with open(AI_CLIENT_TEST_KEYS_FILE, 'r') as f: content = json.load(f)
                if content == {}: os.remove(AI_CLIENT_TEST_KEYS_FILE)
            except: pass
        # Also try to clean up the default one if it was created
        if os.path.exists(DEFAULT_KEYS_FILE):
            try:
                with open(DEFAULT_KEYS_FILE, 'r') as f: content = json.load(f)
                if content == {}: os.remove(DEFAULT_KEYS_FILE)
            except: pass


    def test_01_init_initializes_key_manager(self):
        self.mock_key_manager_class.assert_called_once_with(keys_filepath=AI_CLIENT_TEST_KEYS_FILE)

    def test_02_generate_text_unsupported_provider(self):
        response = self.ai_client.generate_text("Hello", "megacorp_ai")
        self.assertIn("Provider 'megacorp_ai' is not supported", response)
        self.mock_key_manager_instance.get_key.assert_not_called()

    def test_03_generate_text_no_key_available(self):
        self.mock_key_manager_instance.get_key.return_value = None
        provider = "openai"
        response = self.ai_client.generate_text("Hello", provider)

        self.mock_key_manager_instance.get_key.assert_called_once_with(provider)
        self.assertIn(f"No API key available for {provider}", response)
        self.mock_key_manager_instance.update_key_usage.assert_not_called()

    @patch('time.sleep', return_value=None) # Mock time.sleep to speed up tests
    def test_04_generate_text_openai_success(self, mock_sleep):
        mock_api_key = ApiKey(key_value="sk-testkey", provider="openai")
        self.mock_key_manager_instance.get_key.return_value = mock_api_key

        prompt = "What is AI?"
        provider = "openai"
        response = self.ai_client.generate_text(prompt, provider)

        self.mock_key_manager_instance.get_key.assert_called_once_with(provider)
        self.assertIn(f"Mock OpenAI response to: '{prompt}'", response)
        self.assertIn(mock_api_key.key_value[-4:], response)
        self.mock_key_manager_instance.update_key_usage.assert_called_once_with(mock_api_key)
        mock_sleep.assert_called_once() # Ensure sleep was called

    @patch('time.sleep', return_value=None)
    def test_05_generate_text_anthropic_success(self, mock_sleep):
        mock_api_key = ApiKey(key_value="anthropic-testkey", provider="anthropic")
        self.mock_key_manager_instance.get_key.return_value = mock_api_key

        prompt = "Explain quantum physics"
        provider = "anthropic"
        response = self.ai_client.generate_text(prompt, provider)

        self.mock_key_manager_instance.get_key.assert_called_once_with(provider)
        self.assertIn(f"Mock Anthropic response to: '{prompt}'", response)
        self.assertIn(mock_api_key.key_value[-4:], response)
        self.mock_key_manager_instance.update_key_usage.assert_called_once_with(mock_api_key)

    @patch('time.sleep', return_value=None)
    def test_06_generate_text_huggingface_success(self, mock_sleep):
        mock_api_key = ApiKey(key_value="hf-testkey", provider="huggingface")
        self.mock_key_manager_instance.get_key.return_value = mock_api_key

        prompt = "Translate to Spanish: Hello"
        provider = "huggingface"
        response = self.ai_client.generate_text(prompt, provider, model_url="test_model")

        self.mock_key_manager_instance.get_key.assert_called_once_with(provider)
        self.assertIn(f"Mock HuggingFace response to: '{prompt}'", response)
        self.assertIn(mock_api_key.key_value[-4:], response)
        self.mock_key_manager_instance.update_key_usage.assert_called_once_with(mock_api_key)
        # kwargs are passed to generate_text, but the mock doesn't use them beyond the provider string.

    @patch('time.sleep', return_value=None)
    def test_07_generate_text_api_error_openai(self, mock_sleep):
        mock_api_key = ApiKey(key_value="sk-errorkey", provider="openai")
        self.mock_key_manager_instance.get_key.return_value = mock_api_key

        prompt = "trigger error_test" # Mock API error is triggered by "error_test" in prompt
        provider = "openai"
        response = self.ai_client.generate_text(prompt, provider)

        self.mock_key_manager_instance.get_key.assert_called_once_with(provider)
        self.assertIn(f"Error during {provider} API call: Mock OpenAI API error", response)
        self.mock_key_manager_instance.update_key_usage.assert_not_called() # Not called on error

    def test_08_all_supported_providers_covered(self):
        # This test ensures that if we add a provider to SUPPORTED_PROVIDERS,
        # we remember to consider adding a test case for it.
        # It doesn't check for actual implementation, just that it's in the list.
        tested_providers = ["openai", "anthropic", "huggingface"] # Manually list providers with specific tests
        for provider in SUPPORTED_PROVIDERS:
            self.assertIn(provider, tested_providers,
                          f"Provider '{provider}' is in SUPPORTED_PROVIDERS but not explicitly tested in test_ai_client.py mock tests.")

    @patch('time.sleep', return_value=None)
    def test_09_generate_text_with_additional_kwargs(self, mock_sleep):
        mock_api_key = ApiKey(key_value="sk-kwargkey", provider="openai")
        self.mock_key_manager_instance.get_key.return_value = mock_api_key

        prompt = "Test kwargs"
        provider = "openai"
        # These kwargs are not used by the current mock implementation but are passed
        response = self.ai_client.generate_text(prompt, provider, model="gpt-4", temperature=0.7)

        self.mock_key_manager_instance.get_key.assert_called_once_with(provider)
        self.assertIn(f"Mock OpenAI response to: '{prompt}'", response)
        self.mock_key_manager_instance.update_key_usage.assert_called_once_with(mock_api_key)


# It's good practice to ensure dummy files are cleaned up even if tests fail mid-way
# For simplicity, tearDown handles this. If more robustness is needed, try-finally in setUp/tearDown
# or a test runner feature could be used.
import os
import json

if __name__ == '__main__':
    module_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(module_dir))
    unittest.main(verbosity=2)
