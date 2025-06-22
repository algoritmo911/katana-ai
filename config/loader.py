import yaml
import importlib
import os
import inspect
from typing import Optional, Dict, Any # Added Optional, Dict, Any
from nlp_providers.base import NLPProvider
# Importing AdvancedNLPProvider to allow isinstance checks if needed, though not strictly necessary for loading.
from nlp_providers.advanced_base import AdvancedNLPProvider

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "settings.yaml")

def load_config() -> dict:
    """Loads the configuration from settings.yaml."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r') as f:
        config_data = yaml.safe_load(f)
    if not isinstance(config_data, dict):
        raise ValueError("Configuration file is not a valid YAML dictionary.")
    return config_data

def _get_api_key_from_env(config_block: dict, key_name_in_block: str) -> Optional[str]:
    """
    Retrieves an API key from an environment variable specified in the config block.
    Example config_block: {"api_key_env_var": "MY_API_KEY_ENV_NAME"}
    """
    env_var_name = config_block.get(key_name_in_block)
    if env_var_name:
        api_key = os.getenv(env_var_name)
        if not api_key:
            print(f"Warning: Environment variable '{env_var_name}' for API key not found.")
        return api_key
    return None

def get_active_nlp_provider() -> NLPProvider:
    """
    Loads and instantiates the active NLP provider based on the new configuration structure.

    Returns:
        An instance of the configured NLPProvider (or AdvancedNLPProvider).

    Raises:
        ValueError: If the configuration is invalid or the provider cannot be loaded.
    """
    config = load_config()
    active_provider_path_str = config.get("active_nlp_provider")

    if not active_provider_path_str:
        raise ValueError("No 'active_nlp_provider' specified in settings.yaml")

    try:
        # module_name_key is like 'dummy_provider' or 'example_openai_provider'
        # class_name_from_path is like 'DummyProvider' or 'ExampleOpenAIProvider'
        module_name_key, class_name_from_path = active_provider_path_str.rsplit('.', 1)

        full_module_path = f"nlp_providers.{module_name_key}"

        providers_config_section = config.get("providers", {})
        if not isinstance(providers_config_section, dict):
            raise ValueError("'providers' section in settings.yaml is missing or not a dictionary.")

        provider_specific_config = providers_config_section.get(module_name_key)
        if provider_specific_config is None:
            raise ValueError(
                f"No configuration found for provider module '{module_name_key}' "
                f"under 'providers' section in settings.yaml."
            )
        if not isinstance(provider_specific_config, dict):
            raise ValueError(
                f"Configuration for provider module '{module_name_key}' under 'providers' "
                f"section is not a valid dictionary."
            )

        # Determine the actual class name: use from provider's config if specified, else from active_provider_path_str
        actual_class_name = provider_specific_config.get("class", class_name_from_path)

        # Dynamically import the module
        provider_module = importlib.import_module(full_module_path)

        # Get the class from the module
        provider_class = getattr(provider_module, actual_class_name)

        # Prepare config for instantiation:
        # Make a copy to potentially enrich with API keys from env vars
        instantiation_config = provider_specific_config.copy()

        # Example of handling API key from env var for OpenAI-like providers
        # This can be generalized if more providers follow this pattern,
        # or handled within each provider's __init__ method.
        if "api_key_env_var" in instantiation_config and "api_key" not in instantiation_config:
            api_key = _get_api_key_from_env(instantiation_config, "api_key_env_var")
            if api_key:
                instantiation_config["api_key"] = api_key

        if "api_token_env_var" in instantiation_config and "api_token" not in instantiation_config: # For HF
            api_token = _get_api_key_from_env(instantiation_config, "api_token_env_var")
            if api_token:
                instantiation_config["api_token"] = api_token


        # Instantiate the provider
        # Check if the provider's __init__ accepts a config argument
        sig = inspect.signature(provider_class.__init__)
        if 'config' in sig.parameters:
            provider_instance = provider_class(config=instantiation_config)
        else:
            # If provider __init__ doesn't take config, but we have specific config, it's a mismatch.
            # However, some simple providers (like old EchoProvider) might not need it.
            # For providers listed under 'providers' section, they are expected to handle their config.
            if instantiation_config and module_name_key not in ["echo_provider", "dummy_provider"]: # Exclude very simple old ones
                 print(f"Warning: Provider {actual_class_name} does not accept 'config' argument, but config exists.")
            provider_instance = provider_class()
            # If it's a simple provider not expecting detailed config, it might still work.
            # DummyProvider and EchoProvider have been updated to accept config.

        if not isinstance(provider_instance, NLPProvider): # Covers NLPProvider and AdvancedNLPProvider
            raise TypeError(f"Provider {actual_class_name} does not inherit from NLPProvider.")

        return provider_instance

    except ImportError as e:
        raise ValueError(f"Could not import NLP provider module '{full_module_path}': {e}")
    except AttributeError as e:
        raise ValueError(f"Could not find class '{actual_class_name}' in module '{full_module_path}': {e}")
    except Exception as e:
        # Catching generic Exception to provide more context if other errors occur.
        import traceback
        print(f"Detailed error instantiating NLP provider '{active_provider_path_str}': {traceback.format_exc()}")
        raise ValueError(f"Error instantiating NLP provider '{active_provider_path_str}': {e}")


if __name__ == '__main__':
    try:
        print(f"Attempting to load config from: {CONFIG_PATH}")
        cfg = load_config()
        print("\nConfig loaded successfully:")
        print(yaml.dump(cfg, indent=2))

        print("\nAttempting to load active NLP provider...")
        # For this to work, OPENAI_API_KEY env var should be set if active_nlp_provider is example_openai_provider
        # Default in settings.yaml is dummy_provider, which should load fine.
        # You might need to set OPENAI_API_KEY="dummykey" for example_openai_provider to load without real calls.

        # Example: Temporarily set active_nlp_provider for testing specific loader logic
        # cfg["active_nlp_provider"] = "example_openai_provider.ExampleOpenAIProvider" # Requires this file to exist
        # with open(CONFIG_PATH, 'w') as f: # This modifies the actual file! Be careful.
        #    yaml.dump(cfg, f)

        provider = get_active_nlp_provider()
        print(f"\nSuccessfully loaded NLP provider: {provider.name}")
        if hasattr(provider, 'config'):
            print(f"Provider specific config: {provider.config}")

    except Exception as e:
        print(f"\nError during example usage: {e}")
        # print(f"Traceback: {traceback.format_exc()}")
