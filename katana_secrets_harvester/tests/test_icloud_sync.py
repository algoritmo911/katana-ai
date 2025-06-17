
import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone # Added timezone for datetime.now(timezone.utc)
import sys

# Add project root to sys.path to allow 'from katana_secrets_harvester import icloud_sync'
PROJECT_ROOT_FOR_TESTS = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT_FOR_TESTS) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_FOR_TESTS))

from katana_secrets_harvester import icloud_sync

# --- Mock iCloud Note Structure ---
class MockPyiCloudNote:
    def __init__(self, name="Untitled", content="", id_val=None, created=None, last_modified=None):
        self.name = name
        self.title = name
        self.text = content
        self.id = id_val if id_val else str(id(self)) # Simple unique ID for mock
        self.created = created if created else datetime.now(timezone.utc)
        self.last_modified = last_modified if last_modified else datetime.now(timezone.utc)

    def __str__(self): # Make sure str(note_obj) returns the text content
        return self.text

    def __repr__(self):
        return f"<MockPyiCloudNote name='{self.name}' id='{self.id}'>"

# --- Test Cases ---
class TestICloudSyncAuthentication(unittest.TestCase):

    @patch(f'{icloud_sync.__name__}.PyiCloudService')
    def test_login_successful_no_2fa(self, MockPyiCloudService):
        mock_api_instance = MockPyiCloudService.return_value
        mock_api_instance.requires_2fa = False

        api = icloud_sync.get_icloud_service("user", "pass")
        self.assertIsNotNone(api)
        self.assertEqual(api, mock_api_instance)
        MockPyiCloudService.assert_called_once_with("user", "pass")

    @patch(f'{icloud_sync.__name__}.PyiCloudService')
    def test_login_failed(self, MockPyiCloudService):
        MockPyiCloudService.side_effect = icloud_sync.PyiCloudFailedLoginException("Test login failure")
        api = icloud_sync.get_icloud_service("user", "wrong_pass")
        self.assertIsNone(api)

    @patch(f'{icloud_sync.__name__}.PyiCloudService')
    @patch('builtins.input', return_value="123456")
    def test_login_successful_with_2fa(self, mock_input, MockPyiCloudService):
        mock_api_instance = MockPyiCloudService.return_value
        mock_api_instance.requires_2fa = True
        mock_api_instance.validate_2fa_code.return_value = True
        mock_api_instance.is_trusted_session = True

        api = icloud_sync.get_icloud_service("user_2fa", "pass_2fa")
        self.assertIsNotNone(api)
        mock_input.assert_called_once()
        mock_api_instance.validate_2fa_code.assert_called_once_with("123456")

    @patch(f'{icloud_sync.__name__}.PyiCloudService')
    @patch('builtins.input', return_value="wrong_code")
    def test_login_failed_2fa_invalid_code(self, mock_input, MockPyiCloudService):
        mock_api_instance = MockPyiCloudService.return_value
        mock_api_instance.requires_2fa = True
        mock_api_instance.validate_2fa_code.return_value = False
        api = icloud_sync.get_icloud_service("user_2fa", "pass_2fa")
        self.assertIsNone(api)
        mock_api_instance.validate_2fa_code.assert_called_once_with("wrong_code")

class TestICloudSyncParseNotes(unittest.TestCase):
    def test_parse_secrets_from_notes_valid(self):
        mock_notes_service = MagicMock()
        # Use actual newlines for realistic multiline note content
        note1_content = """OPENAI_KEY=sk-123
SERVICE_URL=http://service
#Comment"""
        note2_content = """  TOKEN_A = abc
TOKEN_B=xyz123=extrapart"""
        note1 = MockPyiCloudNote(name="API Keys", content=note1_content)
        note2 = MockPyiCloudNote(name="Tokens", content=note2_content)
        note3 = MockPyiCloudNote(name="Empty", content="")
        note4 = MockPyiCloudNote(name="No Secrets", content="Just some text here.")
        mock_notes_service.all.return_value = [note1, note2, note3, note4]

        secrets = icloud_sync.parse_secrets_from_icloud_notes(mock_notes_service)

        expected_secrets = {
            "OPENAI_KEY": "sk-123",
            "SERVICE_URL": "http://service",
            "TOKEN_A": "abc", # Value is stripped by `value.strip()` in parse_secrets
            "TOKEN_B": "xyz123=extrapart"
        }
        self.assertEqual(secrets, expected_secrets)

    def test_parse_secrets_no_notes(self):
        mock_notes_service = MagicMock()
        mock_notes_service.all.return_value = []
        secrets = icloud_sync.parse_secrets_from_icloud_notes(mock_notes_service)
        self.assertEqual(secrets, {})

    def test_parse_secrets_notes_service_none(self):
        secrets = icloud_sync.parse_secrets_from_icloud_notes(None)
        self.assertEqual(secrets, {})

    def test_parse_secrets_fetch_notes_exception(self):
        mock_notes_service = MagicMock()
        mock_notes_service.all.side_effect = Exception("iCloud API error")
        secrets = icloud_sync.parse_secrets_from_icloud_notes(mock_notes_service)
        self.assertEqual(secrets, {})

class TestICloudSyncSaveSecrets(unittest.TestCase):
    TEST_OUTPUT_DIR_NAME = "temp_test_icloud_save_output" # Unique name
    SECRETS_FILE_STR = f"{TEST_OUTPUT_DIR_NAME}/secrets_temp.json"

    def setUp(self):
        self.test_output_dir_path = Path(self.TEST_OUTPUT_DIR_NAME)
        self.secrets_file_path_obj = Path(self.SECRETS_FILE_STR) # This is a Path object

        self.test_output_dir_path.mkdir(parents=True, exist_ok=True)
        for item in self.test_output_dir_path.glob('*'):
            item.unlink()

    def tearDown(self):
        if self.test_output_dir_path.exists():
            shutil.rmtree(self.test_output_dir_path)

    def test_save_new_secrets_file_creation(self):
        new_secrets = {"icloud_key1": "val1", "icloud_key2": "val2"}
        # Call with string path as per function signature, it resolves to Path inside
        icloud_sync.save_secrets_to_json_merged(new_secrets, output_filename=self.SECRETS_FILE_STR)

        self.assertTrue(self.secrets_file_path_obj.exists())
        with open(self.secrets_file_path_obj, 'r') as f:
            content = json.load(f)
        self.assertEqual(content, new_secrets)
        backups = list(self.test_output_dir_path.glob("*.bak"))
        self.assertEqual(len(backups), 0)

    def test_merge_with_existing_secrets_and_backup(self):
        existing_secrets = {"google_key": "g_val", "common_key": "old_google_val"}
        with open(self.secrets_file_path_obj, 'w') as f: # Use Path object for setup
            json.dump(existing_secrets, f)

        new_icloud_secrets = {"icloud_key": "i_val", "common_key": "new_icloud_val"}
        icloud_sync.save_secrets_to_json_merged(new_icloud_secrets, output_filename=self.SECRETS_FILE_STR)

        expected_merged = {
            "google_key": "g_val",
            "icloud_key": "i_val",
            "common_key": "new_icloud_val"
        }
        with open(self.secrets_file_path_obj, 'r') as f:
            merged_content = json.load(f)
        self.assertEqual(merged_content, expected_merged)

        backups = list(self.test_output_dir_path.glob(f"{self.secrets_file_path_obj.stem}_*.bak"))
        self.assertEqual(len(backups), 1, "Expected one backup file.")
        with open(backups[0], 'r') as bf:
            backup_content = json.load(bf)
        self.assertEqual(backup_content, existing_secrets)

    def test_save_overwriting_corrupted_existing_file(self):
        with open(self.secrets_file_path_obj, 'w') as f:
            f.write("this is not valid json {")

        new_icloud_secrets = {"icloud_key": "i_val_overwrite"}
        icloud_sync.save_secrets_to_json_merged(new_icloud_secrets, output_filename=self.SECRETS_FILE_STR)

        with open(self.secrets_file_path_obj, 'r') as f:
            content = json.load(f)
        # If existing was corrupt, it's backed up, and new file has only new_secrets
        self.assertEqual(content, new_icloud_secrets)

        backups = list(self.test_output_dir_path.glob(f"{self.secrets_file_path_obj.stem}_*.bak"))
        self.assertEqual(len(backups), 1)
        with open(backups[0], 'r') as bf:
            backup_corrupted_content = bf.read()
        self.assertEqual(backup_corrupted_content, "this is not valid json {")

if __name__ == '__main__':
    unittest.main(verbosity=2)
