import unittest
from unittest.mock import patch, MagicMock, ANY
import asyncio
import time
import os
import json

from src.orchestrator.task_orchestrator import TaskOrchestrator, TaskResult
from src.agents.katana_agent import KatanaAgent
# Actual clients are not directly used by this test, but LLMRouter needs them in its namespace
from bot.nlp_clients import OpenAIClient, AnthropicClient, GemmaClient
from bot.nlp_clients.base_nlp_client import NLPServiceError # Import for test

# Mock API keys in environment for LLMRouter to pick up if not in config
os.environ["GEMMA_API_KEY"] = "fake_gemma_key_env"
os.environ["OPENAI_API_KEY"] = "fake_openai_key_env"
os.environ["ANTHROPIC_API_KEY"] = "fake_anthropic_key_env"

# Default router config for KatanaAgent in these tests
# We'll rely on environment variables for API keys primarily,
# but can also demonstrate config overrides.
DEFAULT_ROUTER_CONFIG = {
    "default_model_for_task": {
        "question_answering": "gemma",
        "code_generation": "openai",
        "text_summarization": "anthropic",
        "general_text": "gemma"
    }
}

class TestOrchestratorKatanaIntegration(unittest.TestCase):

    def setUp(self):
        # Patch the actual NLP client classes that LLMRouter would try to instantiate
        # Reverting to plain patch without autospec for class mocks
        self.patch_gemma_client = patch('bot.llm_router.GemmaClient')
        self.MockGemmaClientClass = self.patch_gemma_client.start()
        self.mock_gemma_instance = MagicMock()
        self.MockGemmaClientClass.return_value = self.mock_gemma_instance
        self.mock_gemma_instance.name = "mock_gemma_instance"
        self.mock_gemma_instance.generate_text.return_value = "Default Gemma Mock Response"

        self.patch_openai_client = patch('bot.llm_router.OpenAIClient')
        self.MockOpenAIClientClass = self.patch_openai_client.start()
        self.mock_openai_instance = MagicMock()
        self.MockOpenAIClientClass.return_value = self.mock_openai_instance
        self.mock_openai_instance.name = "mock_openai_instance"
        self.mock_openai_instance.generate_text.return_value = "Default OpenAI Mock Response"

        self.patch_anthropic_client = patch('bot.llm_router.AnthropicClient')
        self.MockAnthropicClientClass = self.patch_anthropic_client.start()
        self.mock_anthropic_instance = MagicMock()
        self.MockAnthropicClientClass.return_value = self.mock_anthropic_instance
        self.mock_anthropic_instance.name = "mock_anthropic_instance"
        self.mock_anthropic_instance.generate_text.return_value = "Default Anthropic Mock Response"

        # Setup a dummy metrics log file
        self.test_metrics_log_file = "test_orchestrator_integration_log.json"
        if os.path.exists(self.test_metrics_log_file):
            os.remove(self.test_metrics_log_file)

    def tearDown(self):
        self.patch_gemma_client.stop()
        self.patch_openai_client.stop()
        self.patch_anthropic_client.stop()
        if os.path.exists(self.test_metrics_log_file):
            os.remove(self.test_metrics_log_file)
        # Clean up env vars if they were specific to tests (though here they are module level for simplicity)
        # For more complex scenarios, manage env vars per test or class.

    async def run_orchestrator_round_async(self, orchestrator, tasks):
        orchestrator.add_tasks(tasks)
        await orchestrator.run_round()

    def test_orchestrator_with_katana_agent_single_successful_task(self):
        # KatanaAgent uses LLMRouter, which uses the mocked clients
        katana = KatanaAgent(router_config=DEFAULT_ROUTER_CONFIG)
        orchestrator = TaskOrchestrator(agent=katana, metrics_log_file=self.test_metrics_log_file)

        # Mock the response from the Gemma client (default for QA)
        self.mock_gemma_instance.generate_text.return_value = "Gemma's answer to the question."

        task = ["What is Katana?"] # This should route to Gemma

        async def main():
            await self.run_orchestrator_round_async(orchestrator, task)
        asyncio.run(main())

        self.assertEqual(len(orchestrator.metrics_history), 1)
        metric = orchestrator.metrics_history[0]
        self.assertEqual(metric['tasks_processed_count'], 1)
        self.assertEqual(metric['successful_tasks_count'], 1)
        self.assertEqual(metric['failed_tasks_count'], 0)
        self.assertEqual(metric['results_summary'][0]['details'], "Gemma's answer to the question.")
        self.assertEqual(metric['results_summary'][0]['success'], True)

        # Router passes api_key=None if not in its direct config. Client then uses env var.
        self.MockGemmaClientClass.assert_called_once_with(api_key=None)

        # KatanaAgent passes preferred_model_provider=None to router if not specified.
        # Router uses this to select client but does not pass it to client's generate_text.
        # LLMRouter calls client.generate_text(prompt, **kwargs) - if kwargs is empty, it's called with positional prompt.
        self.mock_gemma_instance.generate_text.assert_called_once_with("What is Katana?")

        katana.close() # Important to close agent to close router and clients

    def test_orchestrator_with_katana_agent_batch_tasks_mixed_routing(self):
        katana = KatanaAgent(router_config=DEFAULT_ROUTER_CONFIG)
        orchestrator = TaskOrchestrator(agent=katana, batch_size=3, metrics_log_file=self.test_metrics_log_file)

        self.mock_gemma_instance.generate_text.return_value = "Gemma general response."
        self.mock_openai_instance.generate_text.return_value = "OpenAI code snippet."
        self.mock_anthropic_instance.generate_text.return_value = "Anthropic summary."

        tasks = [
            "Tell me a story.", # -> Gemma (general_text)
            "Write a python script for fibonacci.", # -> OpenAI (code_generation)
            "Summarize the concept of AI.", # -> Anthropic (text_summarization)
        ]

        async def main():
            await self.run_orchestrator_round_async(orchestrator, tasks)
        asyncio.run(main())

        self.assertEqual(len(orchestrator.metrics_history), 1)
        metric = orchestrator.metrics_history[0]
        self.assertEqual(metric['tasks_processed_count'], 3)
        self.assertEqual(metric['successful_tasks_count'], 3)

        # Check that each mock client's generate_text was called once with the correct prompt (as positional)
        self.mock_gemma_instance.generate_text.assert_called_once_with("Tell me a story.")
        self.mock_openai_instance.generate_text.assert_called_once_with("Write a python script for fibonacci.")
        self.mock_anthropic_instance.generate_text.assert_called_once_with("Summarize the concept of AI.")

        katana.close()

    def test_orchestrator_task_failure_due_to_nlp_error(self):
        katana = KatanaAgent(router_config=DEFAULT_ROUTER_CONFIG)
        orchestrator = TaskOrchestrator(agent=katana, metrics_log_file=self.test_metrics_log_file)

        test_error_message = "OpenAI API is down via ValueError"
        self.mock_openai_instance.generate_text.side_effect = ValueError(test_error_message)

        task = ["generate code now"] # Simplified prompt to ensure routing to OpenAI

        async def main():
            await self.run_orchestrator_round_async(orchestrator, task)
        asyncio.run(main())

        self.assertEqual(len(orchestrator.metrics_history), 1)
        metric = orchestrator.metrics_history[0]
        self.assertEqual(metric['tasks_processed_count'], 1)

        self.assertEqual(metric['successful_tasks_count'], 0, "Task should have failed")
        self.assertEqual(metric['failed_tasks_count'], 1)

        # This is the path if the exception handling worked correctly
        expected_details = f"Unexpected error in KatanaAgent: {test_error_message}"
        self.assertEqual(metric['results_summary'][0]['details'], expected_details)
        self.assertEqual(metric['results_summary'][0]['success'], False)

        self.mock_openai_instance.generate_text.assert_called_once_with(task[0]) # Use the actual task prompt
        katana.close()

    @patch.object(KatanaAgent, 'handle_task') # Patch KatanaAgent.handle_task directly
    def test_orchestrator_task_failure_direct_agent_error(self, mock_handle_task):
        # KatanaAgent is instantiated, but its handle_task is now a mock
        katana = KatanaAgent(router_config=DEFAULT_ROUTER_CONFIG)
        orchestrator = TaskOrchestrator(agent=katana, metrics_log_file=self.test_metrics_log_file)

        test_error_message = "Direct agent failure (NLPServiceError)"
        # Configure the *mocked* handle_task to raise an NLPServiceError
        mock_handle_task.side_effect = NLPServiceError(test_error_message)

        task = ["This task will fail in agent's mocked handle_task."]

        async def main():
            await self.run_orchestrator_round_async(orchestrator, task)
        asyncio.run(main())

        # Verify our mock agent's handle_task was called
        # It's called with task_prompt and potentially context=None, preferred_model=None
        # KatanaAgent.handle_task signature: (self, task_prompt: str, context: Optional[Dict] = None, preferred_model: Optional[str] = None)
        # Orchestrator calls: self.agent.handle_task(task_prompt=content)
        mock_handle_task.assert_called_once_with(task_prompt=task[0])


        self.assertEqual(len(orchestrator.metrics_history), 1)
        metric = orchestrator.metrics_history[0]
        self.assertEqual(metric['tasks_processed_count'], 1)
        self.assertEqual(metric['successful_tasks_count'], 0, "Task should have failed (direct agent error)")
        self.assertEqual(metric['failed_tasks_count'], 1)
        # The details should be the user_message from the NLPServiceError
        self.assertEqual(metric['results_summary'][0]['details'], test_error_message)
        self.assertEqual(metric['results_summary'][0]['success'], False)

        # katana.close() # Original agent's router wasn't used, so closing is less critical here.
                         # but good practice if other parts of KatanaAgent were real.

    def test_metrics_log_file_creation_and_content(self):
        katana = KatanaAgent(router_config=DEFAULT_ROUTER_CONFIG)
        orchestrator = TaskOrchestrator(agent=katana, metrics_log_file=self.test_metrics_log_file)
        self.mock_gemma_instance.generate_text.return_value = "Logged response"

        async def main():
            await self.run_orchestrator_round_async(orchestrator, ["Log this prompt."])
        asyncio.run(main())

        self.assertTrue(os.path.exists(self.test_metrics_log_file))
        with open(self.test_metrics_log_file, 'r') as f:
            log_data = json.load(f)

        self.assertIsInstance(log_data, list)
        self.assertEqual(len(log_data), 1)
        self.assertEqual(log_data[0]['tasks_processed_count'], 1)
        self.assertEqual(log_data[0]['results_summary'][0]['details'], "Logged response")
        katana.close()

if __name__ == '__main__':
    unittest.main()
