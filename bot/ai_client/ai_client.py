"""
AI Client Module for Katana Bot.

This module provides the `AIClient` class, which acts as an interface to various
AI service providers (e.g., OpenAI, Anthropic, HuggingFace). It utilizes the
`KeyManager` to handle API key selection and rotation.

Current features:
-   Retrieves API keys from `KeyManager`.
-   Supports multiple providers (currently OpenAI, Anthropic, HuggingFace via mock calls).
-   Provides a unified `generate_text` method.
-   Includes mock API call implementations for demonstration and testing.
-   Basic error handling for unsupported providers or unavailable keys.

Future enhancements could include:
-   Actual SDK integrations for each provider.
-   More sophisticated error handling and retry mechanisms.
-   Caching of AI responses.
-   Asynchronous operations.
"""
import logging
import time # For mock API call delay and potential rate limiting
import os
from typing import Optional, List, Dict, Any # For type hinting

# Assuming key_manager is in the same package/directory
from .key_manager import KeyManager, ApiKey, DEFAULT_KEYS_FILE

# Configure logging for this module
logger = logging.getLogger(__name__) # Recommended: Get logger by module name

# Supported AI providers (lowercase for consistent checking)
# This list can be expanded as new provider integrations are added.
SUPPORTED_PROVIDERS: List[str] = ["openai", "anthropic", "huggingface"]

class AIClient:
    """
    Client for interacting with various AI provider SDKs.

    This class abstracts the specifics of each AI provider's API, offering a
    unified method (`generate_text`) to send prompts and receive generated text.
    It uses a `KeyManager` instance to obtain API keys for the requested provider.
    Currently, API calls are mocked; actual SDK integrations are pending.
    """
    def __init__(self, keys_filepath: str = DEFAULT_KEYS_FILE):
        """
        Initializes the AIClient.

        Args:
            keys_filepath (str): Path to the JSON file containing API keys,
                                 passed to the KeyManager. Defaults to `DEFAULT_KEYS_FILE`
                                 from the key_manager module (typically "ai_keys.json").
        """
        # Initialize KeyManager to handle API key retrieval and management.
        # The KeyManager will load keys from the specified file.
        self.key_manager = KeyManager(keys_filepath=keys_filepath)

        # Placeholder for actual SDK client initializations.
        # These would typically be initialized here or lazily upon first use.
        # Example:
        # self.openai_sdk_client = None # Or OpenAI() if configured globally
        # self.anthropic_sdk_client = None
        # self.huggingface_inference_client = None
        logger.info(f"AIClient initialized. KeyManager is configured with keys file: {os.path.abspath(keys_filepath)}")

    def generate_text(self, prompt: str, provider: str, **kwargs: Any) -> str:
        """
        Generates text using the specified AI provider.

        This method selects an API key via KeyManager, then (currently) makes a
        mock API call to the specified provider. It updates key usage on success.

        Args:
            prompt (str): The input prompt for the AI.
            provider (str): The AI provider to use (e.g., "openai", "anthropic").
                            This should be one of the `SUPPORTED_PROVIDERS`. Case-insensitive.
            **kwargs (Any): Additional provider-specific arguments that might be used by
                            actual SDK calls (e.g., model name, max_tokens, temperature).
                            These are logged but not fully utilized by current mock implementations.

        Returns:
            str: The AI-generated text, or an error message string if generation fails
                 (e.g., unsupported provider, no key, API error).
        """
        provider_lower = provider.lower() # Normalize provider name

        if not prompt or not isinstance(prompt, str):
            logger.error("generate_text called with empty or invalid prompt.")
            return "Error: Prompt cannot be empty."

        if provider_lower not in SUPPORTED_PROVIDERS:
            logger.error(f"Unsupported provider '{provider}' requested. Supported: {SUPPORTED_PROVIDERS}")
            return f"Error: Provider '{provider}' is not supported. Supported providers are: {', '.join(SUPPORTED_PROVIDERS)}."

        # Retrieve an API key object from the KeyManager for the specified provider.
        api_key_obj: Optional[ApiKey] = self.key_manager.get_key(provider_lower)

        if not api_key_obj:
            logger.error(f"No API key available in KeyManager for provider '{provider_lower}'.")
            return f"Error: No API key available for provider '{provider_lower}'. Please check your key configuration."

        logger.info(f"Attempting text generation with provider '{provider_lower}' using key ending '...{api_key_obj.key_value[-4:]}'. Prompt: '{prompt[:70]}...'")
        if kwargs:
            logger.debug(f"Additional parameters for {provider_lower}: {kwargs}")

        # --- Mock API Call Section ---
        # In a real implementation, this section would contain calls to the actual AI provider SDKs.
        try:
            # Simulate network delay common in API calls.
            time.sleep(0.5) # Placeholder for actual API call latency.

            if provider_lower == "openai":
                # Mock OpenAI call
                # In a real implementation:
                # from openai import OpenAI
                # client = OpenAI(api_key=api_key_obj.key_value)
                # response = client.chat.completions.create(
                # model=kwargs.get("model", "gpt-3.5-turbo"),
                # messages=[{"role": "user", "content": prompt}]
                # )
                # result = response.choices[0].message.content
                if "error_test" in prompt.lower(): # Mock an API error
                    raise Exception("Mock OpenAI API error")
                result = f"Mock OpenAI response to: '{prompt}' (using key ...{api_key_obj.key_value[-4:]})"

            elif provider_lower == "anthropic":
                # Mock Anthropic call
                # In a real implementation:
                # import anthropic
                # client = anthropic.Anthropic(api_key=api_key_obj.key_value)
                # response = client.messages.create(
                # model=kwargs.get("model", "claude-2"),
                # max_tokens=kwargs.get("max_tokens", 1024),
                # messages=[{"role": "user", "content": prompt}]
                # )
                # result = response.content
                if "error_test" in prompt.lower(): # Mock an API error
                    raise Exception("Mock Anthropic API error")
                result = f"Mock Anthropic response to: '{prompt}' (using key ...{api_key_obj.key_value[-4:]})"

            elif provider_lower == "huggingface":
                # Mock HuggingFace Inference API call
                # In a real implementation, you might use the 'huggingface_hub' library or 'requests'
                # headers = {"Authorization": f"Bearer {api_key_obj.key_value}"}
                # api_url = kwargs.get("model_url", "https://api-inference.huggingface.co/models/gpt2")
                # response = requests.post(api_url, headers=headers, json={"inputs": prompt})
                # response.raise_for_status() # Raise an exception for HTTP errors
                # result = response.json()[0]['generated_text']
                if "error_test" in prompt.lower(): # Mock an API error
                    raise Exception("Mock HuggingFace API error")
                result = f"Mock HuggingFace response to: '{prompt}' (using key ...{api_key_obj.key_value[-4:]})"
            else:
                # Should not happen due to earlier check, but as a safeguard
                return f"Error: Unknown provider '{provider_lower}' in generation logic."

            # If the call was successful (no exception), update key usage
            self.key_manager.update_key_usage(api_key_obj)
            logger.info(f"Successfully generated text with {provider_lower} using key ...{api_key_obj.key_value[-4:]}")
            return result

        except Exception as e:
            logger.error(f"API call failed for {provider_lower} using key ...{api_key_obj.key_value[-4:]}: {e}")
            # Potentially disable the key if it's an authentication error or similar
            # For example, if e is an OpenAI AuthenticationError:
            # if isinstance(e, openai.AuthenticationError):
            #    self.key_manager.disable_key(api_key_obj)
            #    logger.warning(f"Disabled key ...{api_key_obj.key_value[-4:]} for {provider_lower} due to authentication error.")
            # For this mock, we won't disable, but it's an important consideration.
            return f"Error during {provider_lower} API call: {e}"

if __name__ == '__main__':
    # This example assumes ai_keys.json exists or will be created by KeyManager
    # Create a dummy ai_keys.json for this example if it doesn't exist:
    # {
    #   "openai": ["sk-testkey1", "sk-testkey2"],
    #   "anthropic": ["anthropic-testkey1"]
    # }
    import os
    if not os.path.exists(DEFAULT_KEYS_FILE):
        EXAMPLE_KEYS_CONTENT = {
          "openai": [
            "sk-dummy-openai-key-for-ai-client-test1",
            "sk-dummy-openai-key-for-ai-client-test2"
          ],
          "anthropic": [
            "anthropic-dummy-key-for-ai-client-test1"
          ],
          "huggingface": [
            "hf_dummy_key_for_ai_client_test1"
          ]
        }
        with open(DEFAULT_KEYS_FILE, 'w') as f:
            json.dump(EXAMPLE_KEYS_CONTENT, f, indent=2)
        logger.info(f"Created example '{DEFAULT_KEYS_FILE}' for testing ai_client.py")

    ai_client = AIClient()

    print("--- Testing OpenAI ---")
    print(f"Response 1: {ai_client.generate_text('Hello OpenAI!', 'openai')}")
    print(f"Response 2: {ai_client.generate_text('Tell me a joke.', 'openai', model='gpt-4')}") # model is a kwarg
    print(f"Error test: {ai_client.generate_text('This is an error_test for OpenAI.', 'openai')}")


    print("\n--- Testing Anthropic ---")
    print(f"Response: {ai_client.generate_text('Hello Anthropic!', 'anthropic')}")
    print(f"Error test: {ai_client.generate_text('This is an error_test for Anthropic.', 'anthropic')}")

    print("\n--- Testing HuggingFace ---")
    print(f"Response: {ai_client.generate_text('Translate to French: Hello World', 'huggingface', model_url='some_model')}")
    print(f"Error test: {ai_client.generate_text('This is an error_test for HuggingFace.', 'huggingface')}")

    print("\n--- Testing Unsupported Provider ---")
    print(f"Response: {ai_client.generate_text('Hello there!', 'unsupported_provider')}")

    print("\n--- Testing Key Rotation (OpenAI - assuming 2 keys) ---")
    print(f"OpenAI Key 1: {ai_client.generate_text('First call for rotation', 'openai')}")
    print(f"OpenAI Key 2: {ai_client.generate_text('Second call for rotation', 'openai')}")
    print(f"OpenAI Key 1 again: {ai_client.generate_text('Third call for rotation (back to first key)', 'openai')}")

    print("\n--- Testing No Key Scenario (create a new client with non-existent keys file) ---")
    # Create a temporary non-existent keys file path for this test
    non_existent_keys_file = "non_existent_keys.json"
    if os.path.exists(non_existent_keys_file): # Should not exist, but just in case
        os.remove(non_existent_keys_file)

    no_key_client = AIClient(keys_filepath=non_existent_keys_file)
    print(f"OpenAI with no keys file: {no_key_client.generate_text('Test no keys', 'openai')}")

    # Clean up the non_existent_keys.json if KeyManager created an empty one
    if os.path.exists(non_existent_keys_file):
        # Check if it's empty, as KeyManager might create it
        if os.path.getsize(non_existent_keys_file) == 0 or open(non_existent_keys_file).read().strip() == '{}':
             os.remove(non_existent_keys_file)
             logger.info(f"Cleaned up empty '{non_existent_keys_file}'.")
        else:
            logger.warning(f"'{non_existent_keys_file}' was not empty. Did not clean up.")

    # The default ai_keys.json created by this test script might be cleaned up by key_manager.py's main,
    # but it's better to be explicit or ensure content matching if cleanup is desired here.
    # For now, let key_manager.py handle its own example file cleanup if it runs.
    logger.info(f"ai_client.py example finished. If '{DEFAULT_KEYS_FILE}' was created by this script, it might remain.")
