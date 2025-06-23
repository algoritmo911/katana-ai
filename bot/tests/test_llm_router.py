import unittest
from unittest.mock import patch, MagicMock, mock_open
import os

# Assuming NLP clients and BaseNLPClient are in bot.nlp_clients
from bot.nlp_clients import OpenAIClient, AnthropicClient, GemmaClient, BaseNLPClient
from bot.nlp_clients.base_nlp_client import NLPAuthenticationError, NLPServiceError
from bot.llm_router import LLMRouter

# Mock config for tests
MOCK_CONFIG_WITH_KEYS = {
    "OPENAI_API_KEY": "fake_openai_key",
    "ANTHROPIC_API_KEY": "fake_anthropic_key",
    "GEMMA_API_KEY": "fake_gemma_key", # GemmaClient will use this if provided
    "default_model_for_task": {
        "question_answering": "gemma",
        "code_generation": "openai",
        "text_summarization": "anthropic",
        "general_text": "gemma"
    }
}

MOCK_CONFIG_NO_KEYS = { # Clients should try to get keys from env if not provided here
    "default_model_for_task": {
        "question_answering": "gemma",
        "code_generation": "openai",
        "general_text": "gemma"
    }
}


class TestLLMRouter(unittest.TestCase):

    def setUp(self):
        # Patch the actual client classes to control their instantiation and behavior
        # Removing `spec` to simplify mock behavior for call detection
        self.patch_openai = patch('bot.llm_router.OpenAIClient')
        self.patch_anthropic = patch('bot.llm_router.AnthropicClient')
        self.patch_gemma = patch('bot.llm_router.GemmaClient')

        self.MockOpenAIClient = self.patch_openai.start()
        self.MockAnthropicClient = self.patch_anthropic.start()
        self.MockGemmaClient = self.patch_gemma.start()

        # Configure mock instances returned by the mocked classes
        # These are now plain MagicMocks since the class mocks are plain
        self.mock_openai_instance = MagicMock()
        self.mock_anthropic_instance = MagicMock()
        self.mock_gemma_instance = MagicMock()

        self.MockOpenAIClient.return_value = self.mock_openai_instance
        self.MockAnthropicClient.return_value = self.mock_anthropic_instance
        self.MockGemmaClient.return_value = self.mock_gemma_instance

        # Ensure mocks have a name for easier debugging if tests fail
        # (Though this 'name' attribute is for MagicMock's repr, not type name)
        self.mock_openai_instance.name = "mock_openai_instance"
        self.mock_anthropic_instance.name = "mock_anthropic_instance"
        self.mock_gemma_instance.name = "mock_gemma_instance"

    def test_determine_task_type_logic(self): # New test
        router = LLMRouter() # No config needed for this method
        self.assertEqual(router._determine_task_type("write a function for me"), "code_generation")
        self.assertEqual(router._determine_task_type("what is life?"), "question_answering")
        self.assertEqual(router._determine_task_type("summarize this"), "text_summarization")
        self.assertEqual(router._determine_task_type("a neutral statement"), "general_text")
        self.assertEqual(router._determine_task_type("Generate code for a web scraper."), "code_generation")
        self.assertEqual(router._determine_task_type("Can you write a python script to automate email sending?"), "code_generation")


    def tearDown(self):
        self.patch_openai.stop()
        self.patch_anthropic.stop()
        self.patch_gemma.stop()
        # Clear any environment variables set by tests
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMMA_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

    def test_init_with_config(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        self.assertEqual(router.config, MOCK_CONFIG_WITH_KEYS)
        self.assertEqual(router._clients, {})

    def test_init_empty_config(self):
        router = LLMRouter()
        self.assertEqual(router.config, {})
        self.assertEqual(router._clients, {})

    def test_get_client_openai_preferred(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client = router.get_client_for_task("Any prompt", preferred_model_provider="openai")
        self.MockOpenAIClient.assert_called_once_with(api_key="fake_openai_key")
        self.assertIs(client, self.mock_openai_instance)

    def test_get_client_anthropic_preferred(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client = router.get_client_for_task("Any prompt", preferred_model_provider="anthropic")
        self.MockAnthropicClient.assert_called_once_with(api_key="fake_anthropic_key")
        self.assertIs(client, self.mock_anthropic_instance)

    def test_get_client_gemma_preferred(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client = router.get_client_for_task("Any prompt", preferred_model_provider="gemma")
        self.MockGemmaClient.assert_called_once_with(api_key="fake_gemma_key")
        self.assertIs(client, self.mock_gemma_instance)

    def test_get_client_unknown_preferred_raises_value_error(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        with self.assertRaisesRegex(ValueError, "Unknown model provider: unknown"):
            router.get_client_for_task("Any prompt", preferred_model_provider="unknown")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "env_openai_key"}, clear=True)
    def test_get_client_openai_from_env(self):
        router = LLMRouter(config=MOCK_CONFIG_NO_KEYS) # Config has no keys
        client = router.get_client_for_task("Any prompt", preferred_model_provider="openai")
        # OpenAIClient's __init__ is called with api_key=None from router's perspective if not in config.
        # The client itself would then try to fetch from os.environ.
        # Our mock needs to reflect it was called by router with what router knew.
        self.MockOpenAIClient.assert_called_once_with(api_key=None)
        self.assertIs(client, self.mock_openai_instance)

    def test_get_client_initialization_failure_auth(self):
        self.MockGemmaClient.side_effect = NLPAuthenticationError("Gemma auth failed from mock")
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        with self.assertRaisesRegex(NLPAuthenticationError, "Gemma auth failed from mock"):
            router.get_client_for_task("prompt", preferred_model_provider="gemma")

    def test_get_client_initialization_failure_generic(self):
        self.MockAnthropicClient.side_effect = Exception("Anthropic generic init failed")
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        with self.assertRaisesRegex(NLPServiceError, "Failed to initialize client for anthropic: Anthropic generic init failed"):
            router.get_client_for_task("prompt", preferred_model_provider="anthropic")

    def test_client_caching(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client1 = router.get_client_for_task("prompt", preferred_model_provider="openai")
        client2 = router.get_client_for_task("other prompt", preferred_model_provider="openai")
        self.MockOpenAIClient.assert_called_once_with(api_key="fake_openai_key") # Should only be called once
        self.assertIs(client1, self.mock_openai_instance)
        self.assertIs(client2, self.mock_openai_instance)

    # Tests for _determine_task_type and routing based on it
    def test_route_by_task_type_code_generation(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)

        prompt = "write a function" # Simplified prompt, directly matching a keyword
        task_type = router._determine_task_type(prompt)
        self.assertEqual(task_type, "code_generation", f"Task type determination failed for prompt: '{prompt}'")

        default_map = router.config.get("default_model_for_task", {})
        model_provider = default_map.get(task_type)
        self.assertEqual(model_provider, "openai", "Model provider selection from map failed")

        # At this point, model_provider is confirmed to be "openai".
        # The next call effectively tests: router._get_client("openai")
        client = router.get_client_for_task(prompt)

        self.MockOpenAIClient.assert_called_once_with(api_key="fake_openai_key")
        self.assertIs(client, self.mock_openai_instance)

    def test_route_by_task_type_question_answering(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client = router.get_client_for_task("What is the capital of Mars?")
        self.MockGemmaClient.assert_called_once_with(api_key="fake_gemma_key")
        self.assertIs(client, self.mock_gemma_instance)

    def test_route_by_task_type_summarization(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client = router.get_client_for_task("Summarize this long article for me.")
        self.MockAnthropicClient.assert_called_once_with(api_key="fake_anthropic_key")
        self.assertIs(client, self.mock_anthropic_instance)

    def test_route_by_task_type_general_text(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        client = router.get_client_for_task("Tell me a story.") # Falls under general_text
        self.MockGemmaClient.assert_called_once_with(api_key="fake_gemma_key") # Mapped to gemma
        self.assertIs(client, self.mock_gemma_instance)

    def test_route_fallback_to_general_text_default(self):
        custom_config = {
            "default_model_for_task": {
                "question_answering": "openai",
                # no general_text, so should fallback to hardcoded 'gemma' in LLMRouter
            }
        }
        router = LLMRouter(config=custom_config)
        client = router.get_client_for_task("A very generic prompt.")
        self.MockGemmaClient.assert_called_once_with(api_key=None) # No key in this custom_config
        self.assertIs(client, self.mock_gemma_instance)

    def test_route_fallback_to_configured_general_text_default(self):
        custom_config = {
             "OPENAI_API_KEY": "key1", # to satisfy client init if chosen
            "default_model_for_task": {
                "question_answering": "gemma",
                "general_text": "openai" # Explicit general_text default
            }
        }
        router = LLMRouter(config=custom_config)
        client = router.get_client_for_task("A very generic prompt not matching QA.")
        self.MockOpenAIClient.assert_called_once_with(api_key="key1")
        self.assertIs(client, self.mock_openai_instance)

    def test_generate_text_routes_correctly_and_calls_client(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        self.mock_gemma_instance.generate_text.return_value = "Gemma says hello"

        prompt = "What is your purpose?" # Should route to Gemma for QA
        kwargs_to_pass = {"max_tokens": 100, "temperature": 0.5, "scenario": "success"} # scenario for simulated clients

        response = router.generate_text(prompt, **kwargs_to_pass)

        self.MockGemmaClient.assert_called_once_with(api_key="fake_gemma_key")
        self.mock_gemma_instance.generate_text.assert_called_once_with(prompt, **kwargs_to_pass)
        self.assertEqual(response, "Gemma says hello")

    def test_generate_text_with_preference_routes_correctly(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        self.mock_openai_instance.generate_text.return_value = "OpenAI coded something"

        prompt = "What is your purpose?" # Would normally go to Gemma for QA
        preferred_provider = "openai"
        kwargs_to_pass = {"max_tokens": 200, "temperature": 0.8, "scenario": "success"}

        response = router.generate_text(prompt, preferred_model_provider=preferred_provider, **kwargs_to_pass)

        self.MockOpenAIClient.assert_called_once_with(api_key="fake_openai_key")
        self.mock_openai_instance.generate_text.assert_called_once_with(prompt, **kwargs_to_pass)
        self.assertEqual(response, "OpenAI coded something")

    def test_close_all_clients(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        # Initialize a couple of clients
        router.get_client_for_task("Q?", preferred_model_provider="gemma")
        router.get_client_for_task("Code this", preferred_model_provider="openai")

        self.assertTrue("gemma" in router._clients)
        self.assertTrue("openai" in router._clients)

        router.close_all_clients()

        self.mock_gemma_instance.close.assert_called_once()
        self.mock_openai_instance.close.assert_called_once()
        self.assertEqual(router._clients, {}) # Clients cache should be cleared

    def test_close_all_clients_handles_individual_close_errors(self):
        router = LLMRouter(config=MOCK_CONFIG_WITH_KEYS)
        router.get_client_for_task("Q?", preferred_model_provider="gemma")
        router.get_client_for_task("Code this", preferred_model_provider="openai")

        self.mock_gemma_instance.close.side_effect = Exception("Gemma close failed")
        # openai should still be closed

        with patch('builtins.print') as mock_print: # Suppress print output from error
            router.close_all_clients()

        self.mock_gemma_instance.close.assert_called_once()
        self.mock_openai_instance.close.assert_called_once()
        # The client instance is a MagicMock, so type(client).__name__ will be 'MagicMock'
        mock_print.assert_any_call("Error closing client MagicMock: Gemma close failed")
        self.assertEqual(router._clients, {})

    def test_context_manager_closes_clients(self):
        with LLMRouter(config=MOCK_CONFIG_WITH_KEYS) as router:
            router.get_client_for_task("Q?", preferred_model_provider="gemma")
            router.get_client_for_task("Code this", preferred_model_provider="openai")
            # Keep a reference to the mocks to check after __exit__
            gemma_close_mock = self.mock_gemma_instance.close
            openai_close_mock = self.mock_openai_instance.close

        gemma_close_mock.assert_called_once()
        openai_close_mock.assert_called_once()
        self.assertEqual(router._clients, {})


if __name__ == '__main__':
    unittest.main()
