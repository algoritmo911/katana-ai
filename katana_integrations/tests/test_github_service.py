
import unittest
from unittest.mock import patch, MagicMock, PropertyMock, call
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta, timezone # Ensure timezone is imported
import sys

# Add project root to sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from katana_integrations import github_service

# Attempt to import GitHub specific exceptions for more accurate mocking
try:
    from github import GithubException, UnknownObjectException, BadCredentialsException
except ImportError:
    class GithubException(Exception): pass
    class UnknownObjectException(GithubException): pass
    class BadCredentialsException(GithubException): pass


# --- Mock PyGithub Objects ---
class MockGithubCommitAuthor:
    def __init__(self, name="Test Author", email="author@example.com", date=None):
        self.name = name
        self.email = email
        self.date = date if date else datetime.now(timezone.utc)

class MockGithubCommitData:
    def __init__(self, message="Test commit message", author=None, date_override=None):
        self.message = message
        self.author = author if author else MockGithubCommitAuthor(date=date_override)

class MockGithubCommit:
    def __init__(self, sha="test_sha", html_url="http://github.com/commit/test_sha", message="Test commit", author_name="Test Author", author_date=None):
        self.sha = sha
        self.html_url = html_url
        self.commit = MockGithubCommitData(message=message, author=MockGithubCommitAuthor(name=author_name, date=author_date))

class MockGithubRepository:
    def __init__(self, full_name="test_user/test_repo", name="test_repo", description="A test repo",
                 html_url="http://github.com/test_user/test_repo", language="Python",
                 stargazers_count=0, forks_count=0, updated_at=None, fork=False, private=False):
        self.full_name = full_name
        self.name = name
        self.description = description
        self.html_url = html_url
        self.language = language
        self.stargazers_count = stargazers_count
        self.forks_count = forks_count
        self.updated_at = updated_at if updated_at else datetime.now(timezone.utc)
        self.fork = fork
        self.private = private

    def get_commits(self):
        return [MockGithubCommit(sha=f"sha_{i}", message=f"Commit {i}") for i in range(3)]

class MockGithubAuthenticatedUser:
    def __init__(self, login="test_user"):
        self.login = login

    def get_repos(self, sort="updated", direction="desc"):
        return [
            MockGithubRepository(full_name=f"{self.login}/repo1", updated_at=datetime.now(timezone.utc) - timedelta(days=1)),
            MockGithubRepository(full_name=f"{self.login}/repo2", language="JavaScript", updated_at=datetime.now(timezone.utc))
        ]

class MockGithubNotificationSubject:
    def __init__(self, title="Test Notification Title", type="Issue", url="http://api.github.com/subject/1"):
        self.title = title
        self.type = type
        self.url = url

class MockGithubNotification:
    def __init__(self, id="notif_123", reason="mention", unread=True, updated_at=None, last_read_at=None, repo_full_name="test/repo"):
        self.id = id
        self.reason = reason
        self.unread = unread
        self.updated_at = updated_at if updated_at else datetime.now(timezone.utc)
        self.last_read_at = last_read_at
        self.subject = MockGithubNotificationSubject()
        self.repository = MockGithubRepository(full_name=repo_full_name) if repo_full_name else None

def is_iso_timestamp_str(val): # Helper for tests
    if not val: return False
    try:
        datetime.fromisoformat(val.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError): return False

# --- Test Cases ---
class TestGitHubServiceAuthentication(unittest.TestCase):

    @patch.dict(os.environ, {"GITHUB_PAT": "fake_valid_pat"})
    @patch(f"{github_service.__name__}.Github")
    def test_get_github_service_success(self, MockGithub):
        mock_github_instance = MockGithub.return_value
        mock_github_instance.get_user.return_value = MockGithubAuthenticatedUser()
        g = github_service.get_github_service()
        self.assertIsNotNone(g)
        self.assertEqual(g, mock_github_instance)
        MockGithub.assert_called_once_with("fake_valid_pat")
        g.get_user.assert_called_once()

    @patch.dict(os.environ, {"GITHUB_PAT": "fake_invalid_pat"})
    @patch(f"{github_service.__name__}.Github", side_effect=BadCredentialsException(status=401, data={}, headers={}))
    def test_get_github_service_bad_credentials(self, MockGithub):
        g = github_service.get_github_service()
        self.assertIsNone(g)
        MockGithub.assert_called_once_with("fake_invalid_pat")

    @patch.dict(os.environ, {}, clear=True)
    def test_get_github_service_no_pat(self):
        g = github_service.get_github_service()
        self.assertIsNone(g)

class TestGitHubServiceOperations(unittest.TestCase):
    def setUp(self):
        self.g_mock = MagicMock(spec=github_service.Github)
        self.user_mock = MockGithubAuthenticatedUser()
        self.g_mock.get_user.return_value = self.user_mock

    def test_list_user_repos(self):
        self.user_mock.get_repos = MagicMock(return_value=[
            MockGithubRepository(full_name="user/repo1", language="Python"),
            MockGithubRepository(full_name="user/repo2", description="Another repo")
        ])
        repos = github_service.list_user_repos(self.g_mock, max_repos=2)
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["full_name"], "user/repo1")
        self.assertEqual(repos[0]["language"], "Python")
        self.assertTrue(is_iso_timestamp_str(repos[0]["last_updated"]))
        self.user_mock.get_repos.assert_called_once_with(sort="pushed", direction="desc")

    def test_get_repo_commits(self):
        repo_name_to_test = "user/test_repo"
        mock_repo_obj = MockGithubRepository(full_name=repo_name_to_test)
        mock_repo_obj.get_commits = MagicMock(return_value=[
            MockGithubCommit(sha="sha1", message="Commit 1", author_name="Author A", author_date=datetime(2024,1,1,10,0,0, tzinfo=timezone.utc)),
            MockGithubCommit(sha="sha2", message="Commit 2", author_name="Author B", author_date=datetime(2024,1,2,12,0,0, tzinfo=timezone.utc))
        ])
        self.g_mock.get_repo.return_value = mock_repo_obj
        commits = github_service.get_repo_commits(self.g_mock, repo_name_to_test, max_commits=2)
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0]["sha"], "sha1")
        self.assertEqual(commits[0]["author_name"], "Author A")
        self.assertEqual(commits[0]["date_utc"], "2024-01-01T10:00:00+00:00")
        self.g_mock.get_repo.assert_called_once_with(repo_name_to_test)

    def test_get_repo_commits_repo_not_found(self):
        repo_name_to_test = "user/non_existent_repo"
        self.g_mock.get_repo.side_effect = UnknownObjectException(status=404, data={}, headers={})
        commits = github_service.get_repo_commits(self.g_mock, repo_name_to_test)
        self.assertEqual(len(commits), 0)
        self.g_mock.get_repo.assert_called_once_with(repo_name_to_test)

    def test_get_user_notifications(self):
        since_time_dt = datetime.now(timezone.utc) - timedelta(hours=1)
        since_time_iso = since_time_dt.isoformat()

        mock_notifications = [
            MockGithubNotification(id="n1", reason="subscribed", title="Issue Subscribed", unread=True, updated_at=datetime.now(timezone.utc)),
            MockGithubNotification(id="n2", reason="mention", title="PR Mention", unread=False, updated_at=since_time_dt - timedelta(minutes=1))
        ]
        # Filter mock_notifications based on since_time_dt for the expected result
        expected_filtered_notifications = [n for n in mock_notifications if n.updated_at >= since_time_dt]

        self.g_mock.get_notifications = MagicMock(return_value=expected_filtered_notifications)

        notifications = github_service.get_user_notifications(self.g_mock, since_iso=since_time_iso, all_notifications=True) # Test with all=True

        self.g_mock.get_notifications.assert_called_once_with(all=True, participating=False, since=unittest.mock.ANY)
        # Check the datetime object passed to since
        args, kwargs = self.g_mock.get_notifications.call_args
        self.assertEqual(kwargs['since'].replace(microsecond=0), since_time_dt.replace(microsecond=0))

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], "n1")
        self.assertTrue(is_iso_timestamp_str(notifications[0]["updated_at_utc"]))

if __name__ == '__main__':
    unittest.main(verbosity=2)
