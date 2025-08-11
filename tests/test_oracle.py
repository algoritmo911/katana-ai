import unittest
from unittest.mock import patch
from datetime import date

from src.oracle.scanner import GitHubScanner, GitHubAPIError
from src.oracle.models import SpecialistProfile


class TestGitHubScanner(unittest.TestCase):
    """
    Unit tests for the GitHubScanner class.
    """

    @patch('src.oracle.scanner.GitHubScanner._fetch_github_data')
    def test_analyze_success(self, mock_fetch):
        """
        Tests correct profile creation on a successful API-like response.
        """
        # Arrange: Configure the mock to return a dictionary with complete data.
        mock_data = {
            "github_username": "testuser",
            "languages": ["Python", "C++"],
            "skill_level": 7,
            "last_commit_date": date(2023, 10, 26),
        }
        mock_fetch.return_value = mock_data

        # Act: Analyze the user.
        scanner = GitHubScanner()
        profile = scanner.analyze("testuser")

        # Assert: Check that the mock was called and the profile is correct.
        mock_fetch.assert_called_once_with("testuser")
        self.assertIsInstance(profile, SpecialistProfile)
        self.assertEqual(profile.github_username, "testuser")
        self.assertEqual(profile.languages, ["Python", "C++"])
        self.assertEqual(profile.skill_level, 7)
        self.assertEqual(profile.last_commit_date, date(2023, 10, 26))

    @patch('src.oracle.scanner.GitHubScanner._fetch_github_data')
    def test_analyze_no_repositories(self, mock_fetch):
        """
        Tests profile creation for a user with no repository data.
        """
        # Arrange: Configure mock for a user with empty/default data.
        mock_data = {
            "github_username": "emptyuser",
            "languages": [],
            "skill_level": 1,
            "last_commit_date": date(1970, 1, 1),
        }
        mock_fetch.return_value = mock_data

        # Act: Analyze the user.
        scanner = GitHubScanner()
        profile = scanner.analyze("emptyuser")

        # Assert: Check that the mock was called and the profile is correct.
        mock_fetch.assert_called_once_with("emptyuser")
        self.assertIsInstance(profile, SpecialistProfile)
        self.assertEqual(profile.github_username, "emptyuser")
        self.assertEqual(profile.languages, [])
        self.assertEqual(profile.skill_level, 1)

    @patch('src.oracle.scanner.GitHubScanner._fetch_github_data')
    def test_analyze_api_error(self, mock_fetch):
        """
        Tests that a custom GitHubAPIError is raised when the fetch fails.
        """
        # Arrange: Configure the mock to raise a generic exception, simulating a network issue.
        mock_fetch.side_effect = ConnectionError("404 Not Found")

        # Act & Assert: Verify that calling analyze raises the specific GitHubAPIError.
        scanner = GitHubScanner()
        with self.assertRaises(GitHubAPIError) as context:
            scanner.analyze("nonexistentuser")

        # Assert that the original exception is chained for better debugging.
        self.assertIsInstance(context.exception.__cause__, ConnectionError)
        self.assertIn("Failed to analyze profile", str(context.exception))
        mock_fetch.assert_called_once_with("nonexistentuser")
