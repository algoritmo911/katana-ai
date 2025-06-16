
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
    def test_parse_valid_keys(self):
        note_text = "API_KEY=key123\\nOPENAI_KEY = sk-abc\\n# This is a comment\\nSECRET_TOKEN = token_xyz  "
        expected = {"API_KEY": "key123", "OPENAI_KEY": "sk-abc", "SECRET_TOKEN": "token_xyz"}
        self.assertEqual(harvester.parse_keys_from_note_text(note_text), expected)

    def test_parse_empty_text(self):
        self.assertEqual(harvester.parse_keys_from_note_text(""), {})

    def test_parse_no_equals_sign(self):
        note_text = "This is just a line\\nAnother line without equals"
        self.assertEqual(harvester.parse_keys_from_note_text(note_text), {})

    def test_parse_empty_value(self):
        note_text = "EMPTY_KEY=\\nKEY_WITH_SPACE= value"
        expected = {"EMPTY_KEY": "", "KEY_WITH_SPACE": "value"}
        self.assertEqual(harvester.parse_keys_from_note_text(note_text), expected)

    def test_parse_line_starts_with_equals(self):
        note_text = "=value_should_be_ignored"
        self.assertEqual(harvester.parse_keys_from_note_text(note_text), {})

class TestHarvesterSaveSecrets(unittest.TestCase):
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
