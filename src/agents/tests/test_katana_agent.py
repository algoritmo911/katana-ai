import unittest
from unittest.mock import patch, MagicMock, mock_open

from src.agents.katana_agent import KatanaAgent
from bot.llm_router import LLMRouter # KatanaAgent uses LLMRouter
from bot.nlp_clients.base_nlp_client import NLPServiceError

class TestKatanaAgent(unittest.TestCase):

    def setUp(self):
        # We need to mock LLMRouter, which KatanaAgent instantiates.
        self.patch_llm_router = patch('src.agents.katana_agent.LLMRouter', spec=LLMRouter)
        self.MockLLMRouter = self.patch_llm_router.start()

        # This is the mock instance of LLMRouter that KatanaAgent will use
        self.mock_router_instance = MagicMock(spec=LLMRouter)
        self.MockLLMRouter.return_value = self.mock_router_instance

        # Name for easier debugging
        self.mock_router_instance.name = "mock_router_instance"

    def tearDown(self):
        self.patch_llm_router.stop()

    def test_init_default(self):
        agent = KatanaAgent()
        self.MockLLMRouter.assert_called_once_with(config=None)
        self.assertIs(agent.router, self.mock_router_instance)
        self.assertIsNone(agent.default_model_preference)

    def test_init_with_router_config_and_preference(self):
        test_config = {"GEMMA_API_KEY": "test_key"}
        test_preference = "gemma"
        agent = KatanaAgent(router_config=test_config, default_model_preference=test_preference)

        self.MockLLMRouter.assert_called_once_with(config=test_config)
        self.assertIs(agent.router, self.mock_router_instance)
        self.assertEqual(agent.default_model_preference, test_preference)

    def test_handle_task_simple_prompt(self):
        agent = KatanaAgent()
        self.mock_router_instance.generate_text.return_value = "LLM response"

        prompt = "Tell me a story."
        response = agent.handle_task(task_prompt=prompt)

        self.mock_router_instance.generate_text.assert_called_once_with(
            prompt=prompt,
            preferred_model_provider=None # default_model_preference is None
        )
        self.assertEqual(response, "LLM response")

    def test_handle_task_with_context(self):
        agent = KatanaAgent()
        self.mock_router_instance.generate_text.return_value = "Contextual LLM response"

        prompt = "What's next?"
        context = {"topic": "project planning", "previous_step": "analysis"}
        expected_final_prompt = "\n\nContext:\n- topic: project planning\n- previous_step: analysis\n\nTask:\nWhat's next?"

        response = agent.handle_task(task_prompt=prompt, context=context)

        self.mock_router_instance.generate_text.assert_called_once_with(
            prompt=expected_final_prompt,
            preferred_model_provider=None
        )
        self.assertEqual(response, "Contextual LLM response")

    def test_handle_task_with_preferred_model(self):
        agent = KatanaAgent(default_model_preference="gemma") # Default is gemma
        self.mock_router_instance.generate_text.return_value = "OpenAI LLM response"

        prompt = "Write code for this."
        preferred = "openai" # Override default

        response = agent.handle_task(task_prompt=prompt, preferred_model=preferred)

        self.mock_router_instance.generate_text.assert_called_once_with(
            prompt=prompt,
            preferred_model_provider=preferred # Preferred model used
        )
        self.assertEqual(response, "OpenAI LLM response")

    def test_handle_task_uses_default_preference_if_no_override(self):
        agent = KatanaAgent(default_model_preference="anthropic")
        self.mock_router_instance.generate_text.return_value = "Anthropic LLM response"

        prompt = "Explain this concept."

        response = agent.handle_task(task_prompt=prompt) # No preferred_model in call

        self.mock_router_instance.generate_text.assert_called_once_with(
            prompt=prompt,
            preferred_model_provider="anthropic" # Agent's default preference used
        )
        self.assertEqual(response, "Anthropic LLM response")

    def test_handle_task_nlp_service_error_from_router(self):
        agent = KatanaAgent()
        self.mock_router_instance.generate_text.side_effect = NLPServiceError("Router failed", original_error=ValueError("original"))

        prompt = "This will fail."
        with patch('builtins.print') as mock_print: # Suppress KatanaAgent's print
            with self.assertRaisesRegex(NLPServiceError, "Router failed"):
                agent.handle_task(task_prompt=prompt)
            mock_print.assert_any_call("KatanaAgent encountered an NLP Service Error: NLPServiceError: Router failed (Original error: original)")

        self.mock_router_instance.generate_text.assert_called_once_with(
            prompt=prompt,
            preferred_model_provider=None
        )

    def test_handle_task_unexpected_error_from_router(self):
        agent = KatanaAgent()
        self.mock_router_instance.generate_text.side_effect = Exception("Totally unexpected!")

        prompt = "This will also fail."
        with patch('builtins.print') as mock_print: # Suppress KatanaAgent's print
            with self.assertRaisesRegex(NLPServiceError, "Unexpected error in KatanaAgent: Totally unexpected!"):
                agent.handle_task(task_prompt=prompt)
            mock_print.assert_any_call("KatanaAgent encountered an unexpected error: Totally unexpected!")

        self.mock_router_instance.generate_text.assert_called_once_with(
            prompt=prompt,
            preferred_model_provider=None
        )

    def test_close_method(self):
        agent = KatanaAgent()
        with patch('builtins.print') as mock_print: # Suppress agent's print
            agent.close()
        self.mock_router_instance.close_all_clients.assert_called_once()

    def test_context_manager_closes_router(self):
        # Keep a reference to the close method of the mock router instance
        # that will be created when KatanaAgent is instantiated.
        close_method_on_mock_router = self.mock_router_instance.close_all_clients

        with patch('builtins.print') as mock_print: # Suppress agent's print
            with KatanaAgent() as agent:
                self.assertIs(agent.router, self.mock_router_instance)

        close_method_on_mock_router.assert_called_once()

if __name__ == '__main__':
    unittest.main()
