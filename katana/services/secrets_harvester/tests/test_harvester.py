
import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import json
import os
from pathlib import Path
import shutil
import sys

# Add project root to sys.path to allow 'from katana_secrets_harvester import harvester'
# This is necessary for running the test file directly, or for some unittest discovery methods.
PROJECT_ROOT_FOR_TESTS = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT_FOR_TESTS) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_FOR_TESTS))

# Now that sys.path is adjusted, we can import harvester
from katana_secrets_harvester import harvester
# If gkeepapi is part of harvester's global scope, it needs to be mockable there.
# harvester.gkeepapi should work if gkeepapi is imported in harvester.py

# --- Test Data & Mocks ---
MOCK_USERNAME = "testuser@example.com"
MOCK_PASSWORD = "testpassword"
MOCK_API_LABEL_NAME = "api"

class MockGoogleKeepNote:
    def __init__(self, note_id, title, text, labels=None):
        self.id = note_id
        self.title = title
        self.text = text
        self.labels = labels if labels is not None else []
    deleted = False
    def __repr__(self):
        return f"<MockGoogleKeepNote id='{self.id}' title='{self.title}'>"

class MockGoogleKeepLabel:
    def __init__(self, label_id, name):
        self.id = label_id
        self.name = name
    def __repr__(self):
        return f"<MockGoogleKeepLabel id='{self.id}' name='{self.name}'>"

# --- Test Cases ---
class TestHarvesterLogin(unittest.TestCase):
    @patch(f'{harvester.__name__}.gkeepapi.Keep')
    def test_login_successful(self, MockKeep):
        mock_keep_instance = MockKeep.return_value
        mock_keep_instance.login.return_value = True
        keep = harvester.login_keep(MOCK_USERNAME, MOCK_PASSWORD)
        self.assertIsNotNone(keep)
        self.assertEqual(keep, mock_keep_instance)
        mock_keep_instance.login.assert_called_once_with(MOCK_USERNAME, MOCK_PASSWORD)

    @patch(f'{harvester.__name__}.gkeepapi.Keep')
    def test_login_failed(self, MockKeep):
        mock_keep_instance = MockKeep.return_value
        mock_keep_instance.login.return_value = False
        keep = harvester.login_keep(MOCK_USERNAME, MOCK_PASSWORD)
        self.assertIsNone(keep)
        mock_keep_instance.login.assert_called_once_with(MOCK_USERNAME, MOCK_PASSWORD)

    @patch(f'{harvester.__name__}.gkeepapi.Keep')
    def test_login_exception(self, MockKeep):
        mock_keep_instance = MockKeep.return_value
        # Ensure gkeepapi.exception.LoginException is available via harvester's gkeepapi import
        mock_keep_instance.login.side_effect = harvester.gkeepapi.exception.LoginException("Test login error")
        keep = harvester.login_keep(MOCK_USERNAME, MOCK_PASSWORD)
        self.assertIsNone(keep)
        mock_keep_instance.login.assert_called_once_with(MOCK_USERNAME, MOCK_PASSWORD)

class TestHarvesterFindNotes(unittest.TestCase):
    def setUp(self):
        self.mock_keep = MagicMock(spec=harvester.gkeepapi.Keep)
        self.api_label_obj = MockGoogleKeepLabel("label_api_id", MOCK_API_LABEL_NAME)

    def test_find_notes_with_label_success(self):
        note1_text = "API_KEY=123\\nSERVICE_URL=http://service1" # Escaped newline for raw string
        note2_text = "OPENAI_KEY=abc\\nSECRET=xyz"
        mock_note1 = MockGoogleKeepNote("note1", "API Keys 1", note1_text, labels=[self.api_label_obj])
        mock_note2 = MockGoogleKeepNote("note2", "API Keys 2", note2_text, labels=[self.api_label_obj])

        self.mock_keep.findLabel.return_value = self.api_label_obj
        self.mock_keep.find.return_value = iter([mock_note1, mock_note2])

        notes = harvester.find_api_notes(self.mock_keep, MOCK_API_LABEL_NAME)

        self.mock_keep.findLabel.assert_called_once_with(MOCK_API_LABEL_NAME)
        self.mock_keep.find.assert_called_once_with(labels=[self.api_label_obj])
        self.assertEqual(len(notes), 2)
        self.assertIn(mock_note1, notes)
        self.assertIn(mock_note2, notes)

    def test_find_notes_label_not_found(self):
        self.mock_keep.findLabel.return_value = None
        notes = harvester.find_api_notes(self.mock_keep, "non_existent_label")
        self.mock_keep.findLabel.assert_called_once_with("non_existent_label")
        self.mock_keep.find.assert_not_called()
        self.assertEqual(len(notes), 0)

    def test_find_notes_no_notes_with_label(self):
        self.mock_keep.findLabel.return_value = self.api_label_obj
        self.mock_keep.find.return_value = iter([])
        notes = harvester.find_api_notes(self.mock_keep, MOCK_API_LABEL_NAME)
        self.assertEqual(len(notes), 0)

class TestHarvesterParseKeys(unittest.TestCase):
    # --- Tests for is_valid_secret_value (called by parse_keys_from_note_text) ---\n        \n        def test_is_valid_secret_value_known_prefixes(self):\n            # harvester.is_valid_secret_value should be importable.\n            # Assumes harvester module is imported in the test script.\n            self.assertTrue(harvester.is_valid_secret_value("sk-abc123xyz", key_name="OPENAI_KEY"))\n            self.assertTrue(harvester.is_valid_secret_value("patSOME_AIRTABLE_TOKEN.123", key_name="AIRTABLE_PAT"))\n            self.assertTrue(harvester.is_valid_secret_value("pcsk_pinecone_key_here", key_name="PINECONE_KEY"))\n            self.assertTrue(harvester.is_valid_secret_value("AIzaSySOMEGOOGLEAPIKEY", key_name="GOOGLE_API_KEY"))\n            self.assertTrue(harvester.is_valid_secret_value("ghp_githubpersonalaccesstoken", key_name="GITHUB_TOKEN"))\n            self.assertTrue(harvester.is_valid_secret_value("1234567890:AAGxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-abc", key_name="TELEGRAM_BOT_TOKEN"))\n    \n        def test_is_valid_secret_value_invalid_or_non_secret(self):\n            self.assertFalse(harvester.is_valid_secret_value("this is just a normal string", key_name="description"))\n            self.assertFalse(harvester.is_valid_secret_value("sk_almost_but_not_quite", key_name="ALMOST_A_KEY"))\n            self.assertFalse(harvester.is_valid_secret_value("12345:SHORTTOKEN", key_name="TELEGRAM_LIKE_SHORT"))\n            self.assertFalse(harvester.is_valid_secret_value("", key_name="EMPTY_VALUE"))\n            self.assertFalse(harvester.is_valid_secret_value(None, key_name="NONE_VALUE")) # type: ignore\n    \n        # --- Modified tests for parse_keys_from_note_text to reflect filtering ---\n    \n        def test_parse_keys_filters_based_on_valid_value(self):\n            note_text = (\n                "VALID_OPENAI_KEY=sk-thisisavalidkey123\\n" # Using escaped \n for multiline string in test\n                "普通のテキスト=This is just some normal text, not a secret value.\\n"\n                "AIRTABLE_TOKEN=patABCDEFGHIJKLMNOPQRSTUVWXYZ.abcdefghijklmnopqrstuvwxyz0123456789\\n"\n                "MAYBE_USEFUL_INFO=Some project related data that is not a secret pattern.\\n"\n                "TELEGRAM_TOKEN=1234567890:AAGabcdefghijklmnopqrstuvwxyzABCDEFGHIJ\\n"\n                "COMMENTED_KEY=#SECRET_KEY=commentedout\\n"\n                "EMPTY_SECRET_VALUE_KEY= \\n" \n                "KEY_WITH_INVALID_VALUE=notaverysecretlookingstring"\n            )\n            expected_keys = {\n                "VALID_OPENAI_KEY": "sk-thisisavalidkey123",\n                "AIRTABLE_TOKEN": "patABCDEFGHIJKLMNOPQRSTUVWXYZ.abcdefghijklmnopqrstuvwxyz0123456789",\n                "TELEGRAM_TOKEN": "1234567890:AAGabcdefghijklmnopqrstuvwxyzABCDEFGHIJ"\n            }\n            # from unittest.mock import MagicMock # Ensure MagicMock is imported if used\n            # harvester.log_message = MagicMock() # Suppress log output during this specific test if noisy\n            parsed = harvester.parse_keys_from_note_text(note_text)\n            self.assertEqual(parsed, expected_keys)\n    \n        def test_parse_keys_only_non_secrets_in_note(self):\n            note_text = (\n                "ProjectName=Katana\\n"\n                "Version=2.1\\n"\n                "Description=Some notes about the project."\n            )\n            expected_keys = {} \n            parsed = harvester.parse_keys_from_note_text(note_text)\n            self.assertEqual(parsed, expected_keys)\n    \n        def test_parse_keys_mixed_with_comments_and_empty_lines(self):\n            note_text = (\n                "\\n"\n                "# This is a section for OpenAI\\n"\n                "OPENAI_API_KEY=sk-anotherkey789\\n"\n                "\\n"\n                "  # Another commented key: GITHUB_TOKEN=ghp_fakekey\\n"\n                "NOT_A_SECRET_KEY=some data here\\n"\n                "VALID_PAT_KEY=patS3cr3tK3yF0rA1rtable\\n"\n            )\n            expected_keys = {\n                "OPENAI_API_KEY": "sk-anotherkey789",\n                "VALID_PAT_KEY": "patS3cr3tK3yF0rA1rtable"\n            }\n            parsed = harvester.parse_keys_from_note_text(note_text)\n            self.assertEqual(parsed, expected_keys)\n\nclass TestHarvesterSaveSecrets(unittest.TestCase):
    TEST_OUTPUT_DIR_NAME = "temp_test_secrets_output_for_save" # Unique name
    DEFAULT_TEST_FILENAME_STR = f"{TEST_OUTPUT_DIR_NAME}/test_secrets.json"

    def setUp(self):
        self.test_output_dir_path = Path(self.TEST_OUTPUT_DIR_NAME)
        self.default_test_file_path = Path(self.DEFAULT_TEST_FILENAME_STR)

        self.test_output_dir_path.mkdir(parents=True, exist_ok=True)
        for item in self.test_output_dir_path.glob('*'): # Clean up before each test
            item.unlink()

    def tearDown(self):
        if self.test_output_dir_path.exists():
            shutil.rmtree(self.test_output_dir_path)

    # Patching Path.exists and Path.rename for save_secrets_to_json
    @patch(f'{harvester.__name__}.Path.rename')
    @patch(f'{harvester.__name__}.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch(f'{harvester.__name__}.shutil.copyfile') # harvester.py uses shutil.copyfile
    def test_save_secrets_creates_file_no_backup(self, mock_shutil_copy, mocked_file_open, mock_path_exists, mock_path_rename):
        mock_path_exists.return_value = False # Simulate target file does not exist
        data = {"API_KEY": "123"}

        harvester.save_secrets_to_json(data, filename=self.DEFAULT_TEST_FILENAME_STR)

        mocked_file_open.assert_called_once_with(Path(self.DEFAULT_TEST_FILENAME_STR), 'w', encoding='utf-8')
        handle = mocked_file_open()
        # json.dump calls write. Check if write was called (basic check)
        self.assertTrue(handle.write.called)
        mock_shutil_copy.assert_not_called() # No backup should be called

    @patch(f'{harvester.__name__}.Path.rename') # harvester.Path.rename is LOG_FILE.rename
    @patch(f'{harvester.__name__}.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch(f'{harvester.__name__}.shutil.copyfile')
    def test_save_secrets_creates_backup_if_exists(self, mock_shutil_copy, mocked_file_open, mock_path_exists, mock_path_rename):
        # Simulate target file exists, so backup should be created
        # The mock for Path needs to handle different calls to exists()
        # Path(filename).exists() should be True for the original file
        # Path(backup_filename).exists() can be False (doesn't matter for copyfile)
        mock_path_exists.return_value = True

        data = {"NEW_KEY": "xyz"}
        harvester.save_secrets_to_json(data, filename=self.DEFAULT_TEST_FILENAME_STR)

        mock_shutil_copy.assert_called_once() # Backup should be called
        # Check that open was called for writing the new file
        mocked_file_open.assert_called_with(Path(self.DEFAULT_TEST_FILENAME_STR), 'w', encoding='utf-8')

if __name__ == '__main__':
    unittest.main(verbosity=2)
