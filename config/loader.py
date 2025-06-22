import yaml
import importlib
import os
from nlp_providers.base import NLPProvider

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "settings.yaml")

def load_config() -> dict:
    """Loads the configuration from settings.yaml."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    return config

def get_active_nlp_provider() -> NLPProvider:
    """
    Loads and instantiates the active NLP provider based on the configuration.

    Returns:
        An instance of the configured NLPProvider.

    Raises:
        ValueError: If the configuration is invalid or the provider cannot be loaded.
    """
    config = load_config()
    provider_path_str = config.get("active_nlp_provider")

    if not provider_path_str:
        raise ValueError("No 'active_nlp_provider' specified in settings.yaml")

    try:
        module_name, class_name = provider_path_str.rsplit('.', 1)
        full_module_path = f"nlp_providers.{module_name}" # Assuming providers are in nlp_providers

        # Dynamically import the module
        provider_module = importlib.import_module(full_module_path)

        # Get the class from the module
        provider_class = getattr(provider_module, class_name)

        # Get provider-specific config
        provider_config = config.get(module_name, {})

        # Instantiate the provider
        # Check if the provider's __init__ accepts a config argument
        import inspect
        sig = inspect.signature(provider_class.__init__)
        if 'config' in sig.parameters:
            provider_instance = provider_class(config=provider_config)
        else:
            provider_instance = provider_class()

        if not isinstance(provider_instance, NLPProvider):
            raise TypeError(f"Provider {class_name} does not inherit from NLPProvider.")

        return provider_instance

    except ImportError as e:
        raise ValueError(f"Could not import NLP provider module '{full_module_path}': {e}")
    except AttributeError as e:
        raise ValueError(f"Could not find class '{class_name}' in module '{full_module_path}': {e}")
    except Exception as e:
        raise ValueError(f"Error instantiating NLP provider '{provider_path_str}': {e}")

if __name__ == '__main__':
    # Example usage (for testing purposes)
    # This part will fail until dummy_provider is implemented
    try:
        print(f"Attempting to load config from: {CONFIG_PATH}")
        cfg = load_config()
        print("Config loaded successfully:")
        print(yaml.dump(cfg, indent=2))

        # To test get_active_nlp_provider, you'd need a dummy provider implementation.
        # For now, this will likely raise an error until nlp_providers.dummy_provider exists.
        # provider = get_active_nlp_provider()
        # print(f"Successfully loaded NLP provider: {provider.name}")
    except Exception as e:
        print(f"Error during example usage: {e}")
