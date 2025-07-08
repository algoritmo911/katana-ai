import pytest
import os
import toml
from unittest.mock import patch, mock_open

from katana.supabase_client import load_supabase_config, get_supabase_client, SECRETS_FILE

# Test configuration values
TEST_SUPABASE_URL_ENV = "https://test-env.supabase.co"
TEST_SUPABASE_KEY_ENV = "test_env_supabase_key"
TEST_SUPABASE_URL_FILE = "https://test-file.supabase.co"
TEST_SUPABASE_KEY_FILE = "test_file_supabase_key"

@pytest.fixture(autouse=True)
def clear_env_vars():
    """Clears relevant environment variables before each test."""
    original_url = os.environ.pop("SUPABASE_URL", None)
    original_key = os.environ.pop("SUPABASE_KEY", None)
    yield
    if original_url:
        os.environ["SUPABASE_URL"] = original_url
    if original_key:
        os.environ["SUPABASE_KEY"] = original_key

@pytest.fixture
def mock_secrets_file_content():
    return f"""
[supabase]
url = "{TEST_SUPABASE_URL_FILE}"
key = "{TEST_SUPABASE_KEY_FILE}"
"""

def test_load_supabase_config_from_file(mock_secrets_file_content):
    """Test loading configuration from secrets.toml."""
    with patch('builtins.open', mock_open(read_data=mock_secrets_file_content)):
        with patch('os.path.exists', return_value=True): # Ensure os.path.exists(SECRETS_FILE) is true
            url, key = load_supabase_config()
            assert url == TEST_SUPABASE_URL_FILE
            assert key == TEST_SUPABASE_KEY_FILE

def test_load_supabase_config_from_env_vars():
    """Test loading configuration from environment variables when file is not found."""
    os.environ["SUPABASE_URL"] = TEST_SUPABASE_URL_ENV
    os.environ["SUPABASE_KEY"] = TEST_SUPABASE_KEY_ENV
    with patch('builtins.open', side_effect=FileNotFoundError): # Simulate secrets.toml not existing
         with patch('os.path.exists', return_value=False):
            url, key = load_supabase_config()
            assert url == TEST_SUPABASE_URL_ENV
            assert key == TEST_SUPABASE_KEY_ENV

def test_load_supabase_config_priority_file_over_env(mock_secrets_file_content):
    """Test that secrets.toml takes priority over environment variables."""
    os.environ["SUPABASE_URL"] = "env_url_should_be_ignored"
    os.environ["SUPABASE_KEY"] = "env_key_should_be_ignored"
    with patch('builtins.open', mock_open(read_data=mock_secrets_file_content)):
        with patch('os.path.exists', return_value=True):
            url, key = load_supabase_config()
            assert url == TEST_SUPABASE_URL_FILE
            assert key == TEST_SUPABASE_KEY_FILE

def test_load_supabase_config_missing_url_in_file():
    """Test error handling when URL is missing in secrets.toml."""
    mock_content = "[supabase]\nkey = \"some_key\""
    with patch('builtins.open', mock_open(read_data=mock_content)):
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ValueError, match="Supabase URL or Key is missing in secrets.toml"):
                load_supabase_config()

def test_load_supabase_config_missing_key_in_file():
    """Test error handling when key is missing in secrets.toml."""
    mock_content = "[supabase]\nurl = \"some_url\""
    with patch('builtins.open', mock_open(read_data=mock_content)):
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ValueError, match="Supabase URL or Key is missing in secrets.toml"):
                load_supabase_config()

def test_load_supabase_config_missing_url_in_env():
    """Test error handling when SUPABASE_URL is missing from environment variables."""
    os.environ["SUPABASE_KEY"] = TEST_SUPABASE_KEY_ENV
    # Ensure file open is mocked to simulate FileNotFoundError for secrets.toml
    with patch('builtins.open', side_effect=FileNotFoundError):
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ValueError, match="Supabase credentials not found in secrets.toml or environment variables."):
                load_supabase_config()
    # Clean up env var if it was set
    if "SUPABASE_KEY" in os.environ: del os.environ["SUPABASE_KEY"]


def test_load_supabase_config_missing_key_in_env():
    """Test error handling when SUPABASE_KEY is missing from environment variables."""
    os.environ["SUPABASE_URL"] = TEST_SUPABASE_URL_ENV
    with patch('builtins.open', side_effect=FileNotFoundError):
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ValueError, match="Supabase credentials not found in secrets.toml or environment variables."):
                load_supabase_config()
    if "SUPABASE_URL" in os.environ: del os.environ["SUPABASE_URL"]


def test_load_supabase_config_empty_file():
    """Test error handling for an empty secrets.toml."""
    with patch('builtins.open', mock_open(read_data="")):
         with patch('os.path.exists', return_value=True):
            # This might raise toml.TomlDecodeError, which is caught and re-raised as Exception by load_supabase_config
            # Or, if toml.load('') returns {} or None, it will lead to ValueError due to missing keys.
            # Let's refine the expectation based on toml library behavior.
            # toml.load('') raises TomlDecodeError.
            with pytest.raises(Exception): # General exception as load_supabase_config wraps it
                load_supabase_config()


# Mocking create_client for tests that involve get_supabase_client
# This avoids actual client creation during unit tests of the config loading part.
@patch('katana.supabase_client.create_client')
def test_get_supabase_client_success(mock_create_client):
    """Test get_supabase_client when configuration is successful."""
    # Temporarily patch load_supabase_config within the module's scope for this test
    with patch('katana.supabase_client.load_supabase_config', return_value=(TEST_SUPABASE_URL_FILE, TEST_SUPABASE_KEY_FILE)):
        # Since supabase_client is initialized at import time, we need to reload the module
        # or re-trigger its initialization logic. A simpler way for this specific test
        # is to ensure load_supabase_config (which is called at import) behaves as expected.
        # However, the global 'supabase_client' instance is tricky.
        # For this test, let's assume 'get_supabase_client' simply returns the module-level 'supabase_client'.
        # We need to ensure 'supabase_client' gets set.

        # This is a bit of a hack due to module-level client initialization.
        # We are essentially testing that if load_supabase_config works and create_client is called,
        # then get_supabase_client returns the client.
        # A better approach might be to have get_supabase_client initialize on first call if not already.

        # To properly test this, we'd need to reload the module after patching,
        # or ensure the module's initialization logic is re-run.
        import importlib
        import katana.supabase_client

        # Mock the create_client that will be called during the re-import/reload
        mock_client_instance = mock_create_client.return_value

        # Reload the module to re-trigger initialization with patched load_supabase_config
        importlib.reload(katana.supabase_client)

        client = katana.supabase_client.get_supabase_client()
        mock_create_client.assert_called_once_with(TEST_SUPABASE_URL_FILE, TEST_SUPABASE_KEY_FILE)
        assert client == mock_client_instance

@patch('katana.supabase_client.create_client') # Keep this to prevent actual client creation
def test_get_supabase_client_failure_to_load_config(mock_create_client_unused):
    """Test get_supabase_client when configuration fails."""
    with patch('katana.supabase_client.load_supabase_config', side_effect=ValueError("Config load failed")):
        import importlib
        import katana.supabase_client

        # Reload the module. The import-time initialization should fail.
        importlib.reload(katana.supabase_client)

        client = katana.supabase_client.get_supabase_client()
        assert client is None
        # create_client should not have been called
        mock_create_client_unused.assert_not_called()

# To run these tests:
# Ensure pytest and unittest.mock are installed.
# Navigate to the root of your project and run: pytest
# (You might need to set PYTHONPATH=. or install your package in editable mode)

# Example of how SECRETS_FILE is defined in the module, for context:
# SECRETS_FILE = "secrets.toml"
# This test file assumes it's running from a context where SECRETS_FILE can be understood,
# typically by running pytest from the project root.
# The mock_open patches 'builtins.open', so it intercepts file operations regardless of path construction,
# as long as the final path matches what 'open' is called with.
# For 'os.path.exists', we patch it directly.
# The key is that `load_supabase_config` uses `SECRETS_FILE` internally.

# Note on reloading:
# Reloading modules in tests can sometimes be fragile or have side effects if modules
# are not designed to be reloadable. For `supabase_client.py`, the main concern is the
# module-level client initialization. An alternative to reloading is to structure
# `get_supabase_client` to initialize the client on its first call if it hasn't been,
# which makes it easier to test by controlling when `load_supabase_config` is called.
# However, the current tests adapt to the existing structure.

# Cleanup SECRETS_FILE if created by mistake during tests (though mocks should prevent this)
# This is more of a safeguard.
@pytest.fixture(scope="session", autouse=True)
def cleanup_secrets_file_if_exists():
    yield
    if os.path.exists(SECRETS_FILE) and "test-file.supabase.co" in open(SECRETS_FILE).read():
        # A basic check to see if it's our test file, to avoid deleting a real one.
        # This is still risky. Ideally, tests that write files should use temporary directories.
        # Given current tests use mocks for file operations, this shouldn't be necessary.
        # print(f"Warning: Test secrets file {SECRETS_FILE} might have been created. Consider cleanup.")
        pass
