import unittest
from unittest.mock import patch, MagicMock
import os
import requests

from katana.self_heal.git_integration import create_pull_request

class TestGitIntegration(unittest.TestCase):

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPOSITORY": "test/repo"})
    @patch("requests.post")
    def test_create_pull_request_success(self, mock_post):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"html_url": "http://github.com/test/repo/pull/1"}
        mock_post.return_value = mock_response

        # Act
        pr, message = create_pull_request("Test Title", "Test Body", "feat/test")

        # Assert
        self.assertIsNotNone(pr)
        self.assertEqual(pr["html_url"], "http://github.com/test/repo/pull/1")
        mock_post.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_create_pull_request_no_token(self):
        # Act
        pr, message = create_pull_request("Test Title", "Test Body", "feat/test")

        # Assert
        self.assertIsNone(pr)
        self.assertEqual(message, "GITHUB_TOKEN environment variable not set.")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}, clear=True)
    def test_create_pull_request_no_repo(self):
        # Act
        pr, message = create_pull_request("Test Title", "Test Body", "feat/test")

        # Assert
        self.assertIsNone(pr)
        self.assertEqual(message, "GITHUB_REPOSITORY environment variable not set.")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPOSITORY": "test/repo"})
    @patch("requests.post")
    def test_create_pull_request_api_error(self, mock_post):
        # Arrange
        mock_post.side_effect = requests.exceptions.RequestException("API Error")

        # Act
        pr, message = create_pull_request("Test Title", "Test Body", "feat/test")

        # Assert
        self.assertIsNone(pr)
        self.assertIn("Failed to create pull request", message)

if __name__ == "__main__":
    unittest.main()
