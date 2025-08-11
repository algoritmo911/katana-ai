import unittest
from unittest.mock import patch
from katana.self_heal import patch_applicator
import subprocess
import requests

class TestPatchApplicator(unittest.TestCase):

    @patch("subprocess.run")
    def test_restart_service(self, mock_run):
        # Test successful restart
        mock_run.return_value.check_returncode.return_value = 0
        success, message = patch_applicator.restart_service("test_service")
        self.assertTrue(success)
        mock_run.assert_called_with(["sudo", "systemctl", "restart", "test_service"], check=True)

        # Test failed restart
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        success, message = patch_applicator.restart_service("test_service")
        self.assertFalse(success)

    @patch("subprocess.run")
    def test_apply_patch(self, mock_run):
        # Test successful patch application
        mock_run.return_value.check_returncode.return_value = 0
        success, message = patch_applicator.apply_patch("test.patch")
        self.assertTrue(success)
        mock_run.assert_called_with(["git", "apply", "test.patch"], check=True)

        # Test failed patch application
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        success, message = patch_applicator.apply_patch("test.patch")
        self.assertFalse(success)

    @patch("subprocess.run")
    def test_rollback_changes(self, mock_run):
        # Test successful rollback
        mock_run.return_value.check_returncode.return_value = 0
        success, message = patch_applicator.rollback_changes()
        self.assertTrue(success)
        mock_run.assert_called_with(["git", "revert", "HEAD", "--no-edit"], check=True)

        # Test failed rollback
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        success, message = patch_applicator.rollback_changes()
        self.assertFalse(success)


    @patch("requests.get")
    def test_fetch_patch(self, mock_get):
        # Test successful fetch
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.text = "patch content"
        mock_get.return_value = mock_response

        content, message = patch_applicator.fetch_patch("http://example.com/patch")
        self.assertEqual(content, "patch content")

        # Test failed fetch
        mock_get.side_effect = requests.exceptions.RequestException("Failed to connect")
        content, message = patch_applicator.fetch_patch("http://example.com/patch")
        self.assertIsNone(content)


if __name__ == "__main__":
    unittest.main()
