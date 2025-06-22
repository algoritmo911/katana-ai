import unittest
import os
import yaml
from config.loader import load_config, get_active_nlp_provider
from nlp_providers.base import NLPProvider
from nlp_providers.dummy_provider import DummyProvider # Assuming DummyProvider is default
from nlp_providers.echo_provider import EchoProvider

class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        # Create a temporary config file for testing
        self.test_config_path = os.path.join(os.path.dirname(__file__), "..", "config", "test_settings.yaml")
        self.actual_config_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")

        # Backup original settings.yaml if it exists
        self.original_settings_content = None
        if os.path.exists(self.actual_config_path):
            with open(self.actual_config_path, 'r') as f:
                self.original_settings_content = f.read()

        # Create a controlled settings.yaml for tests
        self.test_settings_content = {
            "active_nlp_provider": "dummy_provider.DummyProvider",
            "dummy_provider": {"mode": "test"},
            "echo_provider": {"prefix": "TestEcho: "}
        }
        with open(self.actual_config_path, 'w') as f:
            yaml.dump(self.test_settings_content, f)

        # Ensure config.loader uses this test file path temporarily for get_active_nlp_provider
        # This is a bit tricky as config.loader.CONFIG_PATH is global.
        # A better way would be to allow passing path to load_config and get_active_nlp_provider.
        # For now, we're directly manipulating the actual settings.yaml and restoring it.

    def tearDown(self):
        # Restore original settings.yaml
        if self.original_settings_content:
            with open(self.actual_config_path, 'w') as f:
                f.write(self.original_settings_content)
        elif os.path.exists(self.actual_config_path): # if it was created by test but didn't exist before
            os.remove(self.actual_config_path)

        # Clean up test_settings.yaml if it was created (though setUp currently modifies actual one)
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)


    def test_load_config(self):
        """Test that configuration is loaded correctly."""
        # Temporarily point config.loader.CONFIG_PATH to our test file for this specific test
        # This requires modifying the module's global, which is generally not ideal but common in tests

        original_loader_config_path = ""
        if hasattr(self.get_config_loader_module(), 'CONFIG_PATH'):
             original_loader_config_path = self.get_config_loader_module().CONFIG_PATH

        self.get_config_loader_module().CONFIG_PATH = self.actual_config_path # Use the one we wrote in setUp

        config = load_config()
        self.assertIsNotNone(config)
        self.assertEqual(config.get("active_nlp_provider"), "dummy_provider.DummyProvider")
        self.assertEqual(config.get("dummy_provider", {}).get("mode"), "test")

        if original_loader_config_path: # Restore if it existed
            self.get_config_loader_module().CONFIG_PATH = original_loader_config_path


    def test_get_active_nlp_provider_dummy(self):
        """Test loading the DummyProvider."""
        # Ensure settings.yaml points to DummyProvider
        current_settings = self.test_settings_content.copy()
        current_settings["active_nlp_provider"] = "dummy_provider.DummyProvider"
        with open(self.actual_config_path, 'w') as f:
            yaml.dump(current_settings, f)

        provider = get_active_nlp_provider()
        self.assertIsInstance(provider, NLPProvider)
        self.assertIsInstance(provider, DummyProvider)
        self.assertEqual(provider.name, "DummyProvider")
        self.assertEqual(provider.config.get("mode"), "test")

    def test_get_active_nlp_provider_echo(self):
        """Test loading the EchoProvider and its specific config."""
        # Update settings.yaml to use EchoProvider for this test
        current_settings = self.test_settings_content.copy()
        current_settings["active_nlp_provider"] = "echo_provider.EchoProvider"
        with open(self.actual_config_path, 'w') as f:
            yaml.dump(current_settings, f)

        provider = get_active_nlp_provider()
        self.assertIsInstance(provider, NLPProvider)
        self.assertIsInstance(provider, EchoProvider)
        self.assertEqual(provider.name, "EchoProvider")
        self.assertEqual(provider.prefix, "TestEcho: ")
        self.assertEqual(provider.config.get("prefix"), "TestEcho: ")


    def test_get_active_nlp_provider_missing_config(self):
        """Test error handling for missing active_nlp_provider key."""
        faulty_settings = {"some_other_key": "value"}
        with open(self.actual_config_path, 'w') as f:
            yaml.dump(faulty_settings, f)

        with self.assertRaisesRegex(ValueError, "No 'active_nlp_provider' specified"):
            get_active_nlp_provider()

    def test_get_active_nlp_provider_invalid_module(self):
        """Test error handling for invalid module path."""
        current_settings = self.test_settings_content.copy()
        current_settings["active_nlp_provider"] = "non_existent_module.SomeProvider"
        with open(self.actual_config_path, 'w') as f:
            yaml.dump(current_settings, f)

        with self.assertRaisesRegex(ValueError, "Could not import NLP provider module"):
            get_active_nlp_provider()

    def test_get_active_nlp_provider_invalid_class(self):
        """Test error handling for invalid class name in existing module."""
        current_settings = self.test_settings_content.copy()
        current_settings["active_nlp_provider"] = "dummy_provider.NonExistentClass"
        with open(self.actual_config_path, 'w') as f:
            yaml.dump(current_settings, f)

        with self.assertRaisesRegex(ValueError, "Could not find class 'NonExistentClass'"):
            get_active_nlp_provider()

    def get_config_loader_module(self):
        """ Helper to import config.loader for manipulating its globals if needed.
        Done this way to allow re-importing or accessing the module cleanly.
        """
        import config.loader
        return config.loader

if __name__ == '__main__':
    unittest.main()
