"""
Manages API keys for various AI service providers.

This module defines the `ApiKey` class to represent individual API keys and their
metadata, and the `KeyManager` class to load, store, and provide access to these
keys. Key features include:
- Loading keys from a JSON configuration file (default: 'ai_keys.json').
- Storing keys per provider.
- Round-robin selection of keys for a given provider.
- Tracking usage counts and last used timestamps (basic).
- Enabling/disabling keys.
- Placeholder for future extensions like persistent storage of key modifications.

The expected format for the keys JSON file is:
{
  "provider_name_1": [
    "key_string_1",
    {"key": "key_string_2", "details": {"info": "some_detail"}},
    ...
  ],
  "provider_name_2": [ ... ]
}
"""
import json
import os
from datetime import datetime
import logging
from typing import List, Dict, Optional, Any

# Configure basic logging for this module
# Applications using this module might want to configure logging at a higher level.
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_KEYS_FILE = "ai_keys.json"

class ApiKey:
    """
    Represents an API key and its associated metadata.

    Attributes:
        key_value (str): The actual API key string.
        provider (str): The name of the AI provider (e.g., 'openai', 'anthropic'), stored in lowercase.
        usage_count (int): How many times this key has been used (primarily for rotation or monitoring).
        last_used_at (Optional[datetime]): Timestamp of when the key was last used.
        details (Dict[str, Any]): Provider-specific details or metadata associated with the key.
        enabled (bool): Whether the key is currently active and can be retrieved for use.
    """
    def __init__(self, key_value: str, provider: str, usage_count: int = 0,
                 last_used_at: Optional[datetime] = None, details: Optional[Dict[str, Any]] = None):
        if not key_value or not isinstance(key_value, str):
            raise ValueError("ApiKey 'key_value' must be a non-empty string.")
        if not provider or not isinstance(provider, str):
            raise ValueError("ApiKey 'provider' must be a non-empty string.")

        self.key_value = key_value
        self.provider = provider.lower()
        self.usage_count = usage_count
        self.last_used_at = last_used_at
        self.details = details if details is not None else {}
        self.enabled = True

    def __repr__(self) -> str:
        """Provides a string representation of the ApiKey, obscuring most of the key."""
        return (f"ApiKey(provider='{self.provider}', key_value='...{self.key_value[-4:] if len(self.key_value) > 4 else self.key_value}', "
                f"usage_count={self.usage_count}, enabled={self.enabled}, details={self.details})")

    def increment_usage(self) -> None:
        """Increments the usage count and updates the last used timestamp."""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()

class KeyManager:
    """
    Manages a collection of API keys for different AI providers.

    Loads keys from a specified JSON file and provides methods to retrieve
    keys, typically in a round-robin fashion.
    """
    def __init__(self, keys_filepath: str = DEFAULT_KEYS_FILE):
        """
        Initializes the KeyManager.

        Args:
            keys_filepath (str): Path to the JSON file containing API keys.
                                 Defaults to `DEFAULT_KEYS_FILE` ("ai_keys.json").
        """
        self.keys_filepath = keys_filepath
        self.keys: Dict[str, List[ApiKey]] = {}  # Stores ApiKey objects: provider_name -> [ApiKey, ...]
        self.current_indices: Dict[str, int] = {} # Tracks current index for round-robin: provider_name -> index
        self._load_keys()

    def _load_keys(self) -> None:
        """
        Loads API keys from the JSON file specified in `self.keys_filepath`.
        If the file is not found, it logs a warning and attempts to create an empty one.
        Handles JSON decoding errors.
        """
        if not os.path.exists(self.keys_filepath):
            logger.warning(f"Keys file '{self.keys_filepath}' not found. No keys loaded.")
            try:
                with open(self.keys_filepath, 'w') as f:
                    json.dump({}, f) # Create an empty JSON file
                logger.info(f"Created empty keys file at '{self.keys_filepath}'. Please populate it with API keys.")
            except IOError as e:
                logger.error(f"Could not create empty keys file at '{self.keys_filepath}': {e}")
            return

        try:
            with open(self.keys_filepath, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from '{self.keys_filepath}': {e}")
            return
        except IOError as e:
            logger.error(f"Error reading keys file '{self.keys_filepath}': {e}")
            return

        for provider, provider_keys_data in config.items():
            provider_lower = provider.lower()
            self.keys[provider_lower] = []
            if not isinstance(provider_keys_data, list):
                logger.warning(f"Expected a list of keys for provider '{provider}', got {type(provider_keys_data)}. Skipping.")
                continue

            for key_data in provider_keys_data:
                if isinstance(key_data, str): # Simple list of key strings
                    key_value = key_data
                    details = {}
                elif isinstance(key_data, dict): # More detailed key object
                    key_value = key_data.get("key")
                    if not key_value or not isinstance(key_value, str):
                        logger.warning(f"Invalid or missing 'key' string in key data for provider '{provider}'. Skipping: {key_data}")
                        continue
                    details = key_data.get("details", {})
                else:
                    logger.warning(f"Invalid key entry format for provider '{provider}'. Expected str or dict. Skipping: {key_data}")
                    continue

                self.keys[provider_lower].append(ApiKey(key_value=key_value, provider=provider_lower, details=details))

            if self.keys[provider_lower]:
                self.current_indices[provider_lower] = 0
                logger.info(f"Loaded {len(self.keys[provider_lower])} keys for provider '{provider_lower}'.")
            else:
                logger.warning(f"No valid keys loaded for provider '{provider_lower}'.")


    def get_key(self, provider: str) -> Optional[ApiKey]:
        """
        Retrieves an available API key for the specified provider using a round-robin strategy.
        This method only considers keys that are currently `enabled`.

        Args:
            provider (str): The name of the AI provider (e.g., "openai"). Case-insensitive.

        Returns:
            Optional[ApiKey]: An ApiKey object if an enabled key is found, otherwise None.
        """
        provider_lower = provider.lower()
        if provider_lower not in self.keys or not self.keys[provider_lower]:
            logger.info(f"No keys configured for provider '{provider_lower}'.")
            return None

        provider_keys = self.keys[provider_lower]
        num_keys = len(provider_keys)
        start_index = self.current_indices.get(provider_lower, 0)

        for i in range(num_keys):
            current_key_index = (start_index + i) % num_keys
            key = provider_keys[current_key_index]
            if key.enabled:
                self.current_indices[provider_lower] = (current_key_index + 1) % num_keys
                # key.increment_usage() # Usage should be incremented by the client after successful use
                logger.info(f"Providing key for '{provider_lower}': ...{key.key_value[-4:]}")
                return key

        logger.warning(f"No enabled keys available for provider '{provider_lower}' after checking all.")
        return None

    def update_key_usage(self, key: ApiKey) -> None:
        """
        Updates the usage statistics for a given API key.
        Typically called by the client after a successful API call using the key.

        Args:
            key (ApiKey): The ApiKey object whose usage needs to be updated.
        """
        if not isinstance(key, ApiKey):
            logger.warning("update_key_usage called with non-ApiKey object.")
            return
        key.increment_usage()
        logger.debug(f"Updated usage for key ...{key.key_value[-4:]} (Provider: {key.provider}). New count: {key.usage_count}")

    def disable_key(self, key_to_disable: ApiKey) -> bool:
        """
        Disables a specific key, preventing it from being selected by `get_key`.

        Args:
            key_to_disable (ApiKey): The ApiKey object to disable.

        Returns:
            bool: True if the key was found and disabled, False otherwise.
        """
        if not isinstance(key_to_disable, ApiKey):
            logger.warning("disable_key called with non-ApiKey object.")
            return False

        for provider_keys_list in self.keys.values():
            for key_obj in provider_keys_list:
                if key_obj.key_value == key_to_disable.key_value and key_obj.provider == key_to_disable.provider:
                    if key_obj.enabled:
                        key_obj.enabled = False
                        logger.info(f"Disabled key ...{key_obj.key_value[-4:]} for provider '{key_obj.provider}'.")
                    else:
                        logger.info(f"Key ...{key_obj.key_value[-4:]} for provider '{key_obj.provider}' was already disabled.")
                    return True
        logger.warning(f"Could not find key ...{key_to_disable.key_value[-4:]} (Provider: {key_to_disable.provider}) to disable it.")
        return False

    def enable_key(self, key_to_enable: ApiKey) -> bool:
        """
        Enables a specific key if it was previously disabled, allowing it to be selected by `get_key`.

        Args:
            key_to_enable (ApiKey): The ApiKey object to enable.

        Returns:
            bool: True if the key was found and enabled, False otherwise.
        """
        if not isinstance(key_to_enable, ApiKey):
            logger.warning("enable_key called with non-ApiKey object.")
            return False

        for provider_keys_list in self.keys.values():
            for key_obj in provider_keys_list:
                if key_obj.key_value == key_to_enable.key_value and key_obj.provider == key_to_enable.provider:
                    if not key_obj.enabled:
                        key_obj.enabled = True
                        logger.info(f"Enabled key ...{key_obj.key_value[-4:]} for provider '{key_obj.provider}'.")
                    else:
                        logger.info(f"Key ...{key_obj.key_value[-4:]} for provider '{key_obj.provider}' was already enabled.")
                    return True
        logger.warning(f"Could not find key ...{key_to_enable.key_value[-4:]} (Provider: {key_to_enable.provider}) to enable it.")
        return False

    def add_key(self, provider: str, key_value: str, details: Optional[Dict[str, Any]] = None) -> ApiKey:
        """
        Adds a new key to the manager's in-memory store.
        Note: This change is not automatically persisted to the keys file.
              Call `_save_keys()` explicitly if persistence is needed and implemented.

        Args:
            provider (str): The provider name for the new key.
            key_value (str): The API key string.
            details (Optional[Dict[str, Any]]): Optional dictionary of details for the key.

        Returns:
            ApiKey: The newly created and added ApiKey object.
        """
        provider_lower = provider.lower()
        new_api_key_obj = ApiKey(key_value=key_value, provider=provider_lower, details=details)

        if provider_lower not in self.keys:
            self.keys[provider_lower] = []
            self.current_indices[provider_lower] = 0 # Initialize index for new provider

        self.keys[provider_lower].append(new_api_key_obj)
        logger.info(f"Added new key for provider '{provider_lower}' in-memory. Total keys for this provider: {len(self.keys[provider_lower])}")
        return new_api_key_obj

    def remove_key(self, key_value_to_remove: str, provider: str) -> bool:
        """
        Removes a key from the manager's in-memory store based on its value and provider.
        Note: This change is not automatically persisted to the keys file.
              Call `_save_keys()` explicitly if persistence is needed and implemented.

        Args:
            key_value_to_remove (str): The string value of the key to remove.
            provider (str): The provider from which to remove the key.

        Returns:
            bool: True if a key was found and removed, False otherwise.
        """
        provider_lower = provider.lower()
        if provider_lower in self.keys:
            initial_key_count = len(self.keys[provider_lower])
            # Filter out the key to be removed
            self.keys[provider_lower] = [k for k in self.keys[provider_lower] if k.key_value != key_value_to_remove]

            if len(self.keys[provider_lower]) < initial_key_count:
                logger.info(f"Removed key ending in ...{key_value_to_remove[-4:]} for provider '{provider_lower}' from in-memory store.")
                if not self.keys[provider_lower]: # If list becomes empty
                    self.current_indices.pop(provider_lower, None) # Remove index
                    logger.info(f"No keys left for provider '{provider_lower}' after removal.")
                else:
                    # Adjust current_index to be valid, ensure it doesn't exceed new list length
                    self.current_indices[provider_lower] = min(self.current_indices.get(provider_lower, 0), len(self.keys[provider_lower]) - 1)
                return True
            else:
                logger.warning(f"Key ending in ...{key_value_to_remove[-4:]} for provider '{provider_lower}' not found for removal.")
        else:
            logger.warning(f"Provider '{provider_lower}' not found, cannot remove key.")
        return False

    def _save_keys(self) -> None:
        """
        (Placeholder) Saves the current state of keys back to the JSON file.

        This method would be responsible for serializing the `self.keys` dictionary
        (which contains ApiKey objects) back into the JSON format expected by `_load_keys`
        and writing it to `self.keys_filepath`.

        Important considerations for implementation:
        - How to serialize ApiKey objects (especially `details`, `last_used_at`).
        - Error handling for file I/O.
        - Thread safety if keys can be modified concurrently.
        """
        # Example serialization (conceptual):
        # data_to_save = {}
        # for provider, key_list in self.keys.items():
        #     data_to_save[provider] = []
        #     for api_key_obj in key_list:
        #         key_entry = {"key": api_key_obj.key_value}
        #         if api_key_obj.details:
        #             key_entry["details"] = api_key_obj.details
        #         # Potentially save other fields like usage_count, last_used_at (as ISO string), enabled status
        #         data_to_save[provider].append(key_entry)
        # try:
        #     with open(self.keys_filepath, 'w') as f:
        #         json.dump(data_to_save, f, indent=2)
        #     logger.info(f"Successfully saved keys to {self.keys_filepath}")
        # except IOError as e:
        #     logger.error(f"Failed to save keys to {self.keys_filepath}: {e}")
        logger.warning("(Placeholder) _save_keys() is not fully implemented. Key modifications are in-memory only.")
        pass

if __name__ == '__main__':
# Example Usage (for testing purposes)
# This block helps in direct testing of the key_manager.py script.
# It creates a sample ai_keys.json if one doesn't exist.
    # Example Usage (for testing purposes)
    # Create a dummy ai_keys.json for this example:
    # {
    #   "openai": [
    #     "sk-key1",
    #     {"key": "sk-key2", "details": {"model_preference": "gpt-4"}},
    #     "sk-key3"
    #   ],
    #   "anthropic": [
    #     "anthropic-key1"
    #   ]
    # }
    EXAMPLE_KEYS_CONTENT = {
      "openai": [
        "sk-key1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxX1",
        {"key": "sk-key2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxX2", "details": {"model_preference": "gpt-4"}},
        "sk-key3xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxX3"
      ],
      "anthropic": [
        "anthropic-key1xxxxxxxxxxxxxxxxxxxxxxA1"
      ],
      "anotherprovider": [] # Test empty provider
    }
    if not os.path.exists(DEFAULT_KEYS_FILE):
        with open(DEFAULT_KEYS_FILE, 'w') as f:
            json.dump(EXAMPLE_KEYS_CONTENT, f, indent=2)
        logger.info(f"Created example '{DEFAULT_KEYS_FILE}' for testing key_manager.py")

    key_manager = KeyManager()

    print("\n--- OpenAI Keys ---")
    for _ in range(5):
        key = key_manager.get_key("openai")
        if key:
            print(f"Got key: {key.key_value}, Details: {key.details}")
            key_manager.update_key_usage(key) # Simulate usage
        else:
            print("No OpenAI key available.")
            break

    print("\n--- Anthropic Keys ---")
    key = key_manager.get_key("anthropic")
    if key:
        print(f"Got key: {key.key_value}")
        key_manager.update_key_usage(key)
    else:
        print("No Anthropic key available.")

    print("\n--- Another Provider Keys ---")
    key = key_manager.get_key("anotherprovider")
    if key:
        print(f"Got key: {key.key_value}")
    else:
        print("No AnotherProvider key available.")

    print("\n--- Test Disabling a key ---")
    # It's better to fetch a key first and then disable it, rather than assuming the first key is sk-key1
    # This also tests if get_key correctly cycles
    first_openai_key = key_manager.get_key("openai") # This will be ...X2 because X1 was used in the loop above

    if first_openai_key:
        print(f"First key obtained for disabling test: {first_openai_key}")
        key_manager.disable_key(first_openai_key)
        print(f"Attempting to get OpenAI keys after disabling {first_openai_key.key_value[-4:]}:")
        for i in range(3): # Try to get a few keys
            key_after_disable = key_manager.get_key("openai")
            if key_after_disable:
                print(f" ({i+1}) Got key: {key_after_disable.key_value[-4:]}")
                if key_after_disable.key_value == first_openai_key.key_value:
                    print(f"ERROR: Disabled key {first_openai_key.key_value[-4:]} was returned!")
            else:
                print(f" ({i+1}) No OpenAI key available.")
                break

        key_manager.enable_key(first_openai_key)
        print(f"Re-enabled key: {first_openai_key.key_value[-4:]}")
        key_after_enable = key_manager.get_key("openai")
        if key_after_enable:
             print(f"Got key after re-enable: {key_after_enable.key_value[-4:]} (should be the re-enabled one or the next in cycle if others were used)")
    else:
        print("Could not get an initial OpenAI key to test disabling.")


    # Clean up dummy file if it was created by this script
    # Check if the content is exactly what this script would write to avoid deleting user's file
    if os.path.exists(DEFAULT_KEYS_FILE):
        try:
            with open(DEFAULT_KEYS_FILE, 'r') as f:
                content = json.load(f)
            if content == EXAMPLE_KEYS_CONTENT: # Compare content
                # os.remove(DEFAULT_KEYS_FILE) # Commenting out removal for easier manual testing
                logger.info(f"Example '{DEFAULT_KEYS_FILE}' (created by key_manager.py) was not removed for manual inspection.")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not verify content of '{DEFAULT_KEYS_FILE}' for cleanup: {e}")
