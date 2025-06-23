from bot.llm_router import LLMRouter
from bot.nlp_clients.base_nlp_client import NLPServiceError
from typing import Optional, Dict

class KatanaAgent:
    """
    The main agent for handling tasks using various LLMs via LLMRouter.
    """
    def __init__(self, router_config: Optional[Dict] = None, default_model_preference: Optional[str] = None):
        """
        Initializes KatanaAgent.

        Args:
            router_config: Configuration dictionary for LLMRouter.
                           This can include API keys and default model mappings per task type.
                           Example:
                           {
                               "OPENAI_API_KEY": "sk-...",
                               "ANTHROPIC_API_KEY": "sk-ant-...",
                               "GEMMA_API_KEY": "...",
                               "default_model_for_task": {
                                   "question_answering": "gemma",
                                   "code_generation": "openai",
                                   # etc.
                               }
                           }
            default_model_preference: An optional default model provider (e.g., "openai", "gemma")
                                      to be used if no other preference is derived.
                                      This will be passed to the router's generate_text if set.
        """
        self.router = LLMRouter(config=router_config)
        self.default_model_preference = default_model_preference
        # Note: The `model_preference` from the user's draft for KatanaAgent's init
        # is better suited as `default_model_preference` here, to be passed to
        # router.generate_text, as LLMRouter itself is configured with a broader config dict.

    def handle_task(self, task_prompt: str, context: Optional[Dict] = None, preferred_model: Optional[str] = None) -> str:
        """
        Handles a task by generating a response using LLMRouter.

        Args:
            task_prompt: The textual task or prompt to be processed by the LLM.
            context: Optional dictionary containing additional context for the task.
                     (Currently unused in this basic version, but can be integrated into the prompt).
            preferred_model: Optionally specify a preferred model provider for this specific task,
                             overriding defaults.

        Returns:
            A string containing the LLM's response.

        Raises:
            NLPServiceError: If the LLM router or the underlying client encounters an issue.
        """
        # Basic context integration: prepend to prompt if context exists.
        # More sophisticated context handling might involve specific formatting
        # or passing it to the LLM in a structured way if supported.
        final_prompt = task_prompt
        if context:
            context_str = "\n\nContext:\n" + "\n".join(f"- {k}: {v}" for k, v in context.items())
            final_prompt = context_str + "\n\nTask:\n" + task_prompt

        model_to_use = preferred_model or self.default_model_preference

        try:
            response = self.router.generate_text(prompt=final_prompt, preferred_model_provider=model_to_use)
            # In a real scenario, you might want to structure the response or log it.
            return response
        except NLPServiceError as e:
            # Log the error or handle it more gracefully if needed
            print(f"KatanaAgent encountered an NLP Service Error: {type(e).__name__} - {e}")
            raise  # Re-raise the error to be handled by the caller (e.g., TaskOrchestrator)
        except Exception as e:
            # Catch any other unexpected errors during routing or generation
            print(f"KatanaAgent encountered an unexpected error: {type(e).__name__} - {e}")
            raise NLPServiceError(f"Unexpected error in KatanaAgent: {e}", original_error=e) # Restore original wrapping


    def close(self):
        """
        Closes the LLMRouter and its associated clients.
        Should be called when the agent is no longer needed.
        """
        print("KatanaAgent closing LLMRouter...")
        self.router.close_all_clients()
        print("KatanaAgent LLMRouter closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Example Usage (for quick testing)
if __name__ == '__main__':
    # This example assumes API keys are set as environment variables
    # or you provide them in the router_config.
    # e.g., os.environ["GEMMA_API_KEY"] = "your_gemma_key"

    agent_config = {
        # Example: if you want to pass API keys directly (though env vars are often better)
        # "GEMMA_API_KEY": "your_actual_gemma_api_key_if_not_in_env",
        "default_model_for_task": {
            "question_answering": "gemma",
            "code_generation": "openai", # openai client is simulated, will need scenario if not real
            "text_summarization": "anthropic", # anthropic is simulated
            "general_text": "gemma"
        }
    }

    sample_tasks_with_prefs = [
        ("What is the official language of Brazil?", {"preferred_model": "gemma"}),
        ("Write a Python function that calculates the Nth Fibonacci number.", {"preferred_model": "openai", "kwargs_for_simulated": {"scenario": "success"}}),
        ("Summarize the concept of supply and demand in three sentences.", {"preferred_model": "anthropic", "kwargs_for_simulated": {"scenario": "success"}}),
        ("Tell me a joke about a programmer.", {}), # Uses default routing
        ("What is 2+2?", {"context": {"topic": "basic math"}, "preferred_model": "gemma"}),
    ]

    print("Running KatanaAgent example...")
    try:
        # KatanaAgent can be used as a context manager
        with KatanaAgent(router_config=agent_config, default_model_preference="gemma") as katana:
            for task, params in sample_tasks_with_prefs:
                print(f"\nHandling task: \"{task}\" with params: {params}")
                # The simulated clients (OpenAI, Anthropic) might need a 'scenario' kwarg.
                # The real Gemma client does not.
                # LLMRouter's generate_text should pass through any additional kwargs.

                # For the example, we need to pass 'scenario' if the chosen model is simulated
                # This logic is a bit complex for a simple __main__ and would not exist in prod
                # where clients are expected to be "real".

                # Simplified: We pass all params directly to handle_task, which passes to router.
                # The router will pass them to the specific client.
                # Our simulated clients accept `scenario` through **kwargs.

                # Reconstruct preferred_model and context to pass to handle_task
                current_pref = params.get("preferred_model")
                current_context = params.get("context")

                # The 'kwargs_for_simulated' would be passed into router.generate_text
                # via katana.handle_task -> self.router.generate_text(..., **kwargs)
                # However, handle_task doesn't explicitly take **kwargs to pass through.
                # Let's assume for this example that if preferred_model is openai/anthropic,
                # we are in a "test" mode and pass scenario.
                # This is not ideal for a __main__ but shows the flow.

                # The `handle_task` doesn't currently accept arbitrary `**kwargs` to pass down.
                # The `router.generate_text` *does*.
                # For the test, we'll assume that if we target a simulated client,
                # the necessary 'scenario' would be part of the `router_config` or handled
                # by a more sophisticated test setup.
                # For now, this example might only fully work for Gemma or if simulated clients
                # have a default 'success' scenario.
                # The OpenAIClient and AnthropicClient were updated to take 'scenario' from kwargs.

                # Let's refine the example to be more direct for now.
                # We will rely on the default "success" scenario in the simulated clients if not specified.
                # OR, the router's config could specify default kwargs for certain clients.

                response_text = katana.handle_task(task_prompt=task, context=current_context, preferred_model=current_pref)
                print(f"  Agent Response: {response_text}")

    except NLPServiceError as e:
        print(f"Service Error during KatanaAgent example: {e.user_message}")
        if e.original_error:
            print(f"  Original error details: {e.original_error}")
    except ImportError as e:
        print(f"ImportError: {e}. Make sure all NLP client dependencies are installed (e.g., google-generativeai).")
    except Exception as e:
        print(f"An unexpected error occurred in KatanaAgent example: {type(e).__name__} - {e}")

    print("\nKatanaAgent example finished.")
