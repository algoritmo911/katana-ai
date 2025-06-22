import unittest
import os
import json
from datetime importdatetime
from unittest.mock import patch, mock_open

# Ensure the logger in key_manager doesn't output during tests unless specifically testing logging
import logging
logging.getLogger('bot.ai_client.key_manager').setLevel(logging.CRITICAL)

# Add bot/ai_client to sys.path if KeyManager is not found.
# This is often needed if tests are run from the project root.
import sys
from pathlib import Path
# Assuming this test file is in bot/ai_client/test_key_manager.py
# and key_manager.py is in bot/ai_client/
# Adjust if your structure is different or if you use a test runner that handles paths
# current_dir = Path(__file__).parent
# project_root = current_dir.parent.parent # Adjust based on actual depth
# sys.path.insert(0, str(current_dir)) # Add current dir to find key_manager
# sys.path.insert(0, str(project_root)) # Add project root for broader imports if needed

from key_manager import KeyManager, ApiKey, DEFAULT_KEYS_FILE

TEST_KEYS_FILE = "test_ai_keys.json"
MOCK_KEYS_CONTENT = {
    "openai": [
        "sk-key1",
        {"key": "sk-key2", "details": {"priority": 1}},
        "sk-key3"
    ],
    "anthropic": [
        "anthropic-key1"
    ],
    "emptyprovider": []
}

class TestKeyManager(unittest.TestCase):

    def setUp(self):
        # Create a dummy test keys file
        with open(TEST_KEYS_FILE, 'w') as f:
            json.dump(MOCK_KEYS_CONTENT, f, indent=2)
        self.key_manager = KeyManager(keys_filepath=TEST_KEYS_FILE)

    def tearDown(self):
        # Remove the dummy test keys file
        if os.path.exists(TEST_KEYS_FILE):
            os.remove(TEST_KEYS_FILE)
        # Also remove the default file if it was created by a test for missing file
        if os.path.exists(DEFAULT_KEYS_FILE):
            # Only remove if it's an empty JSON object, indicating it was auto-created
            try:
                with open(DEFAULT_KEYS_FILE, 'r') as f:
                    content = json.load(f)
                    if content == {}:
                        os.remove(DEFAULT_KEYS_FILE)
            except (IOError, json.JSONDecodeError):
                pass # Ignore if not readable or not valid JSON

    def test_01_load_keys_success(self):
        self.assertIn("openai", self.key_manager.keys)
        self.assertEqual(len(self.key_manager.keys["openai"]), 3)
        self.assertIsInstance(self.key_manager.keys["openai"][0], ApiKey)
        self.assertEqual(self.key_manager.keys["openai"][0].key_value, "sk-key1")
        self.assertEqual(self.key_manager.keys["openai"][1].key_value, "sk-key2")
        self.assertEqual(self.key_manager.keys["openai"][1].details, {"priority": 1})

        self.assertIn("anthropic", self.key_manager.keys)
        self.assertEqual(len(self.key_manager.keys["anthropic"]), 1)
        self.assertEqual(self.key_manager.keys["anthropic"][0].key_value, "anthropic-key1")

        self.assertIn("emptyprovider", self.key_manager.keys)
        self.assertEqual(len(self.key_manager.keys["emptyprovider"]), 0)

    def test_02_load_keys_file_not_found(self):
        if os.path.exists("non_existent_keys.json"): # Should not exist
            os.remove("non_existent_keys.json")

        # Suppress logger output for this specific test of warning
        with patch.object(logging.getLogger('bot.ai_client.key_manager'), 'warning') as mock_log_warning:
            km = KeyManager(keys_filepath="non_existent_keys.json")
            self.assertEqual(km.keys, {}) # No keys loaded
            mock_log_warning.assert_any_call("Keys file 'non_existent_keys.json' not found. No keys loaded.")

        # Check if an empty file was created (as per current KeyManager logic)
        self.assertTrue(os.path.exists("non_existent_keys.json"))
        with open("non_existent_keys.json", 'r') as f:
            self.assertEqual(json.load(f), {})
        os.remove("non_existent_keys.json")


    def test_03_load_keys_invalid_json(self):
        with open(TEST_KEYS_FILE, 'w') as f:
            f.write("this is not json")

        with patch.object(logging.getLogger('bot.ai_client.key_manager'), 'error') as mock_log_error:
            km = KeyManager(keys_filepath=TEST_KEYS_FILE)
            self.assertEqual(km.keys, {})
            mock_log_error.assert_any_call(f"Error decoding JSON from '{TEST_KEYS_FILE}': Expecting value: line 1 column 1 (char 0)")


    def test_04_get_key_round_robin(self):
        # OpenAI has 3 keys
        key1 = self.key_manager.get_key("openai")
        self.assertIsNotNone(key1)
        self.assertEqual(key1.key_value, "sk-key1")

        key2 = self.key_manager.get_key("openai")
        self.assertIsNotNone(key2)
        self.assertEqual(key2.key_value, "sk-key2")

        key3 = self.key_manager.get_key("openai")
        self.assertIsNotNone(key3)
        self.assertEqual(key3.key_value, "sk-key3")

        key4 = self.key_manager.get_key("openai") # Should wrap around
        self.assertIsNotNone(key4)
        self.assertEqual(key4.key_value, "sk-key1")

    def test_05_get_key_unknown_provider(self):
        key = self.key_manager.get_key("unknown_provider")
        self.assertIsNone(key)

    def test_06_get_key_empty_provider(self):
        key = self.key_manager.get_key("emptyprovider")
        self.assertIsNone(key)

    def test_07_update_key_usage(self):
        key = self.key_manager.get_key("openai")
        self.assertIsNotNone(key)
        self.assertEqual(key.usage_count, 0)
        self.assertIsNone(key.last_used_at)

        self.key_manager.update_key_usage(key)
        self.assertEqual(key.usage_count, 1)
        self.assertIsNotNone(key.last_used_at)
        self.assertIsInstance(key.last_used_at, datetime)

    def test_08_disable_enable_key(self):
        openai_keys = self.key_manager.keys["openai"]
        key_to_disable = openai_keys[0] # sk-key1

        # Initial state: all enabled
        self.assertTrue(key_to_disable.enabled)

        # Disable the key
        self.assertTrue(self.key_manager.disable_key(key_to_disable))
        self.assertFalse(key_to_disable.enabled)

        # Try to get sk-key1, should get sk-key2 instead
        retrieved_key1 = self.key_manager.get_key("openai")
        self.assertIsNotNone(retrieved_key1)
        self.assertEqual(retrieved_key1.key_value, "sk-key2") # Next key

        retrieved_key2 = self.key_manager.get_key("openai")
        self.assertIsNotNone(retrieved_key2)
        self.assertEqual(retrieved_key2.key_value, "sk-key3") # Next key

        # All other keys used up, now trying to get a key should return None as sk-key1 is disabled
        retrieved_key3 = self.key_manager.get_key("openai")
        self.assertIsNone(retrieved_key3) # sk-key1 is disabled, sk-key2 and sk-key3 already "handed out" by round robin

        # Reset indices for a cleaner test of disable effect
        self.key_manager.current_indices["openai"] = 0

        k = self.key_manager.get_key("openai") # Should skip sk-key1
        self.assertEqual(k.key_value, "sk-key2")
        k = self.key_manager.get_key("openai") # Should be sk-key3
        self.assertEqual(k.key_value, "sk-key3")
        k = self.key_manager.get_key("openai") # Should be None as sk-key1 is disabled
        self.assertIsNone(k)


        # Enable the key back
        self.assertTrue(self.key_manager.enable_key(key_to_disable))
        self.assertTrue(key_to_disable.enabled)

        # Reset index and try again, should get sk-key1 now
        self.key_manager.current_indices["openai"] = 0
        key_after_enable = self.key_manager.get_key("openai")
        self.assertIsNotNone(key_after_enable)
        self.assertEqual(key_after_enable.key_value, "sk-key1")

    def test_09_disable_non_existent_key(self):
        non_existent_api_key = ApiKey(key_value="does-not-exist", provider="openai")
        self.assertFalse(self.key_manager.disable_key(non_existent_api_key))

    def test_10_get_key_all_disabled(self):
        # Disable all openai keys
        for key_obj in self.key_manager.keys["openai"]:
            self.key_manager.disable_key(key_obj)

        key = self.key_manager.get_key("openai")
        self.assertIsNone(key)

        # Re-enable one for cleanup / further tests if any
        if self.key_manager.keys["openai"]:
            self.key_manager.enable_key(self.key_manager.keys["openai"][0])

    def test_11_add_key_in_memory(self):
        provider = "new_provider"
        new_key_value = "new-key-123"
        self.assertNotIn(provider, self.key_manager.keys)

        new_api_key_obj = self.key_manager.add_key(provider, new_key_value, details={"info": "test"})
        self.assertIn(provider, self.key_manager.keys)
        self.assertEqual(len(self.key_manager.keys[provider]), 1)
        self.assertEqual(self.key_manager.keys[provider][0].key_value, new_key_value)
        self.assertEqual(self.key_manager.keys[provider][0].details, {"info": "test"})
        self.assertEqual(new_api_key_obj.key_value, new_key_value)

        # Test getting the new key
        retrieved_key = self.key_manager.get_key(provider)
        self.assertIsNotNone(retrieved_key)
        self.assertEqual(retrieved_key.key_value, new_key_value)

    def test_12_remove_key_in_memory(self):
        provider = "openai"
        key_to_remove = "sk-key2" # This key exists

        self.assertTrue(any(k.key_value == key_to_remove for k in self.key_manager.keys[provider]))
        initial_key_count = len(self.key_manager.keys[provider])

        removed = self.key_manager.remove_key(key_to_remove, provider)
        self.assertTrue(removed)
        self.assertEqual(len(self.key_manager.keys[provider]), initial_key_count - 1)
        self.assertFalse(any(k.key_value == key_to_remove for k in self.key_manager.keys[provider]))

        # Test removing a non-existent key
        removed_non_existent = self.key_manager.remove_key("non-existent-key", provider)
        self.assertFalse(removed_non_existent)

        # Test removing from non-existent provider
        removed_other_provider = self.key_manager.remove_key("sk-key1", "no_such_provider")
        self.assertFalse(removed_other_provider)


if __name__ == '__main__':
    # If running this file directly, ensure 'bot.ai_client' is discoverable
    # This setup helps if you run 'python test_key_manager.py' from bot/ai_client/
    # For running with 'python -m unittest discover', this might not be necessary
    # if your project structure and __init__.py files are correct.

    # Construct the path to the 'bot' directory, assuming test_key_manager.py is in bot/ai_client/
    # Path(__file__).parent is bot/ai_client
    # Path(__file__).parent.parent is bot/
    # Path(__file__).parent.parent.parent is the project root

    # To make 'from key_manager ...' work, 'bot/ai_client' must be in sys.path
    # To make 'from bot.ai_client...' work, project root must be in sys.path AND bot/__init__.py must exist

    module_dir = Path(__file__).resolve().parent
    # If key_manager is in the same directory as this test file:
    sys.path.insert(0, str(module_dir))
    # If key_manager is in a parent or sibling, adjust accordingly or ensure your PYTHONPATH is set.

    unittest.main(verbosity=2)
