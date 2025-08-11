import unittest
import os
import shutil
from unittest.mock import patch, MagicMock

from katana.self_heal.patch_validator import PatchValidator

class TestPatchValidator(unittest.TestCase):

    def setUp(self):
        self.validator = PatchValidator()
        self.test_file = "test_file.py"
        self.original_content = "def test_func():\n    assert 1 == 2\n"
        with open(self.test_file, "w") as f:
            f.write(self.original_content)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        backup_path = f"{self.test_file}.bak"
        if os.path.exists(backup_path):
            os.remove(backup_path)

    @patch("subprocess.run")
    def test_validate_patch_success(self, mock_subprocess_run):
        # Arrange
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        original_snippet = "assert 1 == 2"
        patched_snippet = "assert 1 == 1"

        # Act
        is_valid = self.validator.validate_patch(self.test_file, original_snippet, patched_snippet)

        # Assert
        self.assertTrue(is_valid)
        with open(self.test_file, "r") as f:
            content = f.read()
        self.assertEqual(content, self.original_content) # Check file is restored

    @patch("subprocess.run")
    def test_validate_patch_failure(self, mock_subprocess_run):
        # Arrange
        mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="Test failed", stderr="")
        original_snippet = "assert 1 == 2"
        patched_snippet = "assert 1 == 3" # Still wrong

        # Act
        is_valid = self.validator.validate_patch(self.test_file, original_snippet, patched_snippet)

        # Assert
        self.assertFalse(is_valid)
        with open(self.test_file, "r") as f:
            content = f.read()
        self.assertEqual(content, self.original_content) # Check file is restored

    def test_validate_patch_file_not_found(self):
        # Act
        is_valid = self.validator.validate_patch("non_existent_file.py", "", "")

        # Assert
        self.assertFalse(is_valid)

if __name__ == "__main__":
    unittest.main()
