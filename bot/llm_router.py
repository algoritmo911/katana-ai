from bot.nlp_clients import OpenAIClient, AnthropicClient, GemmaClient, BaseNLPClient
from bot.nlp_clients.base_nlp_client import NLPAuthenticationError, NLPServiceError

class LLMRouter:
    """
    Routes requests to the appropriate LLM client based on task type or explicit model preference.
    """
    def __init__(self, config: dict = None):
        """
        Initializes the LLMRouter.

        Args:
            config: A configuration dictionary that might contain API keys
                    or default model preferences. Example:
                    {
                        "openai_api_key": "sk-...",
                        "anthropic_api_key": "sk-ant-...",
                        "gemma_api_key": "...",
                        "default_model_for_task": {
                            "question_answering": "gemma",
                            "code_generation": "openai",
                            "text_summarization": "anthropic",
                            "general_text": "gemma"
                        }
                    }
        """
        self.config = config or {}
        self._clients = {} # Cache for initialized clients

    def _get_client(self, model_provider: str) -> BaseNLPClient:
        """
        Lazily initializes and returns a client for the specified model provider.

        Args:
            model_provider: The name of the model provider (e.g., "openai", "anthropic", "gemma").

        Returns:
            An instance of the NLP client.

        Raises:
            ValueError: If the model provider is unknown.
            NLPAuthenticationError: If API key is missing for the provider.
        """
        if model_provider in self._clients:
            return self._clients[model_provider]

        api_key = None
        client_class = None

        if model_provider == "openai":
            api_key = self.config.get("OPENAI_API_KEY") # Consistent with how GemmaClient expects env var
            client_class = OpenAIClient
        elif model_provider == "anthropic":
            api_key = self.config.get("ANTHROPIC_API_KEY")
            client_class = AnthropicClient
        elif model_provider == "gemma":
            # GemmaClient will look for GEMMA_API_KEY in env if not provided,
            # but we can also pass it via config for consistency.
            api_key = self.config.get("GEMMA_API_KEY")
            client_class = GemmaClient
        else:
            raise ValueError(f"Unknown model provider: {model_provider}")

        if not client_class: # Should not happen if model_provider is valid
             raise ValueError(f"No client class found for provider: {model_provider}")

        try:
            # Pass api_key explicitly; if None, individual clients might try env vars
            client = client_class(api_key=api_key)
            self._clients[model_provider] = client
            return client
        except NLPAuthenticationError as e:
            raise e # Re-raise specific auth error
        except Exception as e: # Catch other init errors
            raise NLPServiceError(f"Failed to initialize client for {model_provider}: {e}", original_error=e)


    def _determine_task_type(self, prompt: str) -> str:
        """
        Determines the task type based on the prompt.
        This is a basic implementation and can be expanded.
        """
        prompt_lower = prompt.lower()
        if "generate code" in prompt_lower or "write a function" in prompt_lower or "python script" in prompt_lower:
            return "code_generation"
        elif "summarize" in prompt_lower or "tl;dr" in prompt_lower:
            return "text_summarization"
        elif "?" in prompt or prompt_lower.startswith("what is") or prompt_lower.startswith("who is"):
            return "question_answering"
        # Add more rules for analytics, etc.
        return "general_text"

    def get_client_for_task(self, prompt: str, preferred_model_provider: str = None) -> BaseNLPClient:
        """
        Gets the best NLP client based on the task type inferred from the prompt
        or an explicitly preferred model.

        Args:
            prompt: The user's prompt.
            preferred_model_provider: Optional. If provided, this model provider will be used directly.
                                      (e.g., "openai", "anthropic", "gemma")

        Returns:
            An instance of BaseNLPClient.
        """
        if preferred_model_provider:
            return self._get_client(preferred_model_provider.lower())

        task_type = self._determine_task_type(prompt)

        default_map = self.config.get("default_model_for_task", {})
        model_provider = default_map.get(task_type)

        if not model_provider:
            # Fallback to a general default if task-specific default isn't set
            model_provider = default_map.get("general_text", "gemma") # Default to gemma if no other specified

        return self._get_client(model_provider)

    def generate_text(self, prompt: str, preferred_model_provider: str = None, **kwargs) -> str:
        """
        Routes the prompt to the appropriate LLM and generates text.

        Args:
            prompt: The input prompt.
            preferred_model_provider: Explicitly choose a model provider (e.g., "openai").
            **kwargs: Additional arguments for the underlying client's generate_text method
                      (e.g., max_tokens, temperature).

        Returns:
            The generated text.
        """
        client = self.get_client_for_task(prompt, preferred_model_provider)
        return client.generate_text(prompt, **kwargs)

    def close_all_clients(self):
        """Closes all initialized NLP clients."""
        for client in self._clients.values():
            try:
                client.close()
            except Exception as e:
                # Log error or handle as appropriate, but don't let one client's failure
                # prevent others from closing.
                print(f"Error closing client {type(client).__name__}: {e}")
        self._clients.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all_clients()

# Example Usage (for quick testing)
if __name__ == '__main__':
    # For this example to run, you might need to set environment variables for API keys
    # e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMMA_API_KEY
    # Or pass them in the config:
    router_config = {
        # "OPENAI_API_KEY": "your_openai_key_here_or_set_env",
        # "ANTHROPIC_API_KEY": "your_anthropic_key_here_or_set_env",
        # "GEMMA_API_KEY": "your_gemma_key_here_or_set_env", # Gemma client can also pick from os.environ['GEMMA_API_KEY']
        "default_model_for_task": {
            "question_answering": "gemma", # Assuming Gemma is good for QA
            "code_generation": "openai",   # Assuming OpenAI is good for code
            "text_summarization": "anthropic", # Assuming Anthropic for summarization
            "general_text": "gemma"        # Default fallback
        }
    }

    prompts_and_prefs = [
        ("What is the capital of France?", None),
        ("Write a python function to sort a list.", None),
        ("Summarize the following text: Katana is a framework...", None),
        ("Tell me a short story.", None),
        ("Generate a SQL query to find users.", "openai"), # Preferred
        ("Explain quantum computing simply.", "gemma"), # Preferred
        ("What is your name?", "anthropic") # Preferred
    ]

    # It's good practice to use the router as a context manager if it holds resources
    # like client connections, though for these simulated clients it's less critical.
    try:
        with LLMRouter(config=router_config) as router:
            for prompt_text, preference in prompts_and_prefs:
                print(f"\nPrompt: \"{prompt_text}\" (Preference: {preference or 'auto'})")
                try:
                    # For simulated clients, we might need to pass a 'scenario' if they expect one
                    # For real clients, this would be actual generation parameters.
                    # Here, we assume the underlying clients are the simulated ones
                    # which might need a 'scenario' kwarg for their generate_text.
                    # If they are real clients, this is fine.
                    # For this test, let's assume 'success' for simulated ones.
                    kwargs_for_simulated = {}
                    # Determine client to pass scenario if it's a simulated one
                    # This is a bit meta for a simple example
                    # For actual use, you won't need 'scenario'
                    _client_for_prompt = router.get_client_for_task(prompt_text, preference)
                    if isinstance(_client_for_prompt, (OpenAIClient, AnthropicClient)):
                         kwargs_for_simulated['scenario'] = 'success'


                    response = router.generate_text(prompt_text, preferred_model_provider=preference, **kwargs_for_simulated)
                    print(f"  Routed to: {type(router.get_client_for_task(prompt_text, preference)).__name__}")
                    print(f"  Response: {response}")
                except NLPServiceError as e:
                    print(f"  Error: {e}")
                except ValueError as e:
                     print(f"  Configuration Error: {e}")
                except Exception as e:
                    print(f"  Unexpected error: {type(e).__name__} - {e}")
    except NLPAuthenticationError as e:
        print(f"A client failed to authenticate: {e}")
    except Exception as e:
        print(f"General error with router setup or usage: {e}")

    print("\nDemonstrating direct client fetching and error for unknown provider:")
    try:
        with LLMRouter(config=router_config) as router:
            client = router._get_client("gemma") # Assuming GEMMA_API_KEY is set or in config
            print(f"Fetched client: {type(client).__name__}")
            # client = router._get_client("unknown_provider") # This should fail
            # print(f"Fetched client: {type(client).__name__}")
    except Exception as e:
        print(f"Error: {e}")

    print("\nDemonstrating missing API key for a specific client (if not in env or config):")
    # Example: if "OPENAI_API_KEY" is not in router_config and not in os.environ
    # and OpenAIClient strictly requires it on init (which our refactored one does)
    lean_config = {"default_model_for_task": {"code_generation": "openai"}}
    # Make sure OPENAI_API_KEY is not in env for this to reliably show the auth error from client
    # For testing this part, you might need to os.environ.pop('OPENAI_API_KEY', None)
    # This is hard to demo without manipulating global env state here.
    # The individual clients' __init__ methods are responsible for raising NLPAuthenticationError.
    # The router's _get_client method will propagate that.
    print("(Skipping direct demo of missing API key for brevity, relies on client's own checks)")
