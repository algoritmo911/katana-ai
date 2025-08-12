import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path
import importlib
from datetime import datetime, timezone

# Adjust sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Module to be tested
gs_module_path = 'katana.services.api_integrations.github_service'
github_service_module = None
PyGithubErrorTypes = MagicMock() # Placeholder if PyGithub is not installed

try:
    from katana.services.api_integrations import github_service as github_service_module
    # Attempt to import PyGithub exceptions for more accurate mocking
    try:
        from github import GithubException, UnknownObjectException, BadCredentialsException
        PyGithubErrorTypes.GithubException = GithubException
        PyGithubErrorTypes.UnknownObjectException = UnknownObjectException
        PyGithubErrorTypes.BadCredentialsException = BadCredentialsException
    except ImportError:
        # Define dummy exceptions if PyGithub is not installed, so tests can be defined
        class GithubException(Exception): pass
        class UnknownObjectException(GithubException): pass
        class BadCredentialsException(GithubException): pass
        PyGithubErrorTypes.GithubException = GithubException
        PyGithubErrorTypes.UnknownObjectException = UnknownObjectException
        PyGithubErrorTypes.BadCredentialsException = BadCredentialsException
        print("Warning: PyGithub not installed. Using dummy exceptions for github_service tests.")

except KeyError as e: # For KATANA_LOG_LEVEL
    if 'KATANA_LOG_LEVEL' in str(e):
        os.environ['KATANA_LOG_LEVEL'] = 'INFO'
        from katana.services.api_integrations import github_service as github_service_module
    else:
        raise
except ImportError as e:
    print(f"ImportError loading github_service: {e}")

class TestGitHubService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if 'KATANA_LOG_LEVEL' not in os.environ:
            os.environ['KATANA_LOG_LEVEL'] = 'INFO'
        global github_service_module
        # Reload the module to ensure KATANA_LOG_LEVEL is respected if set here
        # and to ensure the global 'github_service_module' is the reloaded one.
        try:
            if github_service_module:
                 github_service_module = importlib.reload(github_service_module)
            elif gs_module_path in sys.modules:
                 github_service_module = importlib.reload(sys.modules[gs_module_path])
            else:
                 github_service_module = importlib.import_module(gs_module_path)
        except ImportError:
            github_service_module = None


    def setUp(self):
        if not github_service_module:
            self.skipTest("github_service module could not be loaded.")

        # Reload module before each test for clean state, esp. global PYGITHUB_AVAILABLE
        globals()['github_service_module'] = importlib.reload(github_service_module)

        self.logger_patch = patch(f'{gs_module_path}.logger', new_callable=MagicMock)
        self.mock_logger = self.logger_patch.start()
        self.addCleanup(self.logger_patch.stop)

        self.getenv_patch = patch(f'{gs_module_path}.os.getenv') # Patch within module's context
        self.mock_getenv = self.getenv_patch.start()
        self.addCleanup(self.getenv_patch.stop)

        self.github_class_patch = patch(f'{gs_module_path}.Github', autospec=True)
        self.mock_github_class = self.github_class_patch.start()
        self.addCleanup(self.github_class_patch.stop)
        self.mock_github_instance = self.mock_github_class.return_value
        # Explicitly add the method that the autospec might miss on the instance
        self.mock_github_instance.get_notifications = MagicMock()

    def test_get_github_service_success(self):
        self.mock_getenv.return_value = 'test_pat_value'
        mock_user = MagicMock()
        mock_user.login = 'testuser'
        self.mock_github_instance.get_user.return_value = mock_user

        g = github_service_module.get_github_service()
        self.assertIsNotNone(g)
        self.mock_getenv.assert_called_once_with('GITHUB_PAT')
        self.mock_github_class.assert_called_once_with('test_pat_value')
        self.mock_github_instance.get_user.assert_called_once()
        self.mock_logger.info.assert_any_call("Successfully authenticated with GitHub as user: testuser")

    def test_get_github_service_no_pat(self):
        self.mock_getenv.return_value = None
        g = github_service_module.get_github_service()
        self.assertIsNone(g)
        self.mock_logger.critical.assert_any_call("GITHUB_PAT environment variable not set. Cannot authenticate with GitHub.")

    def test_get_github_service_bad_credentials(self):
        self.mock_getenv.return_value = 'invalid_pat_value'
        # Ensure the correct error type is used (from PyGithubErrorTypes if available)
        self.mock_github_instance.get_user.side_effect = PyGithubErrorTypes.BadCredentialsException(status=401, data={'message': 'Bad credentials'}, headers=None)

        g = github_service_module.get_github_service()
        self.assertIsNone(g)
        self.mock_logger.error.assert_any_call("GitHub authentication failed: Bad credentials (invalid PAT?).")

    def test_get_github_service_github_exception(self):
        self.mock_getenv.return_value = 'test_pat_value'
        self.mock_github_instance.get_user.side_effect = PyGithubErrorTypes.GithubException(status=500, data={'message': 'Server error'}, headers=None)

        g = github_service_module.get_github_service()
        self.assertIsNone(g)
        self.mock_logger.error.assert_any_call("A GitHub API error occurred during authentication: 500 {'message': 'Server error'}")

    @patch(f'{gs_module_path}.PYGITHUB_AVAILABLE', False)
    def test_get_github_service_pygithub_not_available(self):
        reloaded_gs_module = importlib.reload(sys.modules[gs_module_path])

        g = reloaded_gs_module.get_github_service()
        self.assertIsNone(g)
        self.mock_logger.critical.assert_any_call("Cannot proceed: PyGithub library is not installed.")

    # --- Start of newly added methods ---
    def test_list_user_repos_success(self):
        self.mock_getenv.return_value = 'test_pat'
        mock_repo1 = MagicMock()
        mock_repo1.full_name = 'user/repo1'
        mock_repo1.name = 'repo1'
        mock_repo1.description = 'Test repo 1'
        mock_repo1.html_url = 'http://github.com/user/repo1'
        mock_repo1.language = 'Python'
        mock_repo1.stargazers_count = 10
        mock_repo1.forks_count = 2
        mock_repo1.updated_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_repo1.fork = False
        mock_repo1.private = False

        mock_user_obj = MagicMock() # Renamed from mock_user to avoid conflict if self.mock_github_instance.get_user was already called
        mock_user_obj.get_repos.return_value = [mock_repo1]
        self.mock_github_instance.get_user.return_value = mock_user_obj

        g = github_service_module.get_github_service()
        repos = github_service_module.list_user_repos(g, max_repos=1)

        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]['full_name'], 'user/repo1')
        self.mock_logger.info.assert_any_call("Fetching up to 1 repositories for authenticated user...")
        self.mock_logger.info.assert_any_call("Fetched 1 repositories.")

    def test_list_user_repos_api_error(self):
        self.mock_getenv.return_value = 'test_pat'
        mock_user_obj = MagicMock()
        mock_user_obj.get_repos.side_effect = PyGithubErrorTypes.GithubException(status=500, data={}, headers=None)
        self.mock_github_instance.get_user.return_value = mock_user_obj

        g = github_service_module.get_github_service()
        repos = github_service_module.list_user_repos(g)
        self.assertEqual(len(repos), 0)
        self.mock_logger.error.assert_any_call("GitHub API error listing repositories: 500 {}")

    def test_get_repo_commits_success(self):
        self.mock_getenv.return_value = 'test_pat'
        mock_commit_data = MagicMock()
        mock_commit_data.author.name = 'Test Author'
        mock_commit_data.author.email = 'author@example.com'
        mock_commit_data.author.date = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_commit_data.message = 'Test commit message'

        mock_commit = MagicMock()
        mock_commit.sha = 'abcdef123456'
        mock_commit.commit = mock_commit_data
        mock_commit.html_url = 'http://github.com/user/repo/commit/abcdef123456'

        mock_repo_obj = MagicMock()
        mock_repo_obj.get_commits.return_value = [mock_commit]
        self.mock_github_instance.get_repo.return_value = mock_repo_obj

        g = github_service_module.get_github_service()
        commits = github_service_module.get_repo_commits(g, 'user/repo1', max_commits=1)

        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]['sha'], 'abcdef123456')
        self.assertEqual(commits[0]['message'], 'Test commit message')
        self.mock_logger.info.assert_any_call("Fetching last 1 commits for repository: user/repo1...")

    def test_get_repo_commits_repo_not_found(self):
        self.mock_getenv.return_value = 'test_pat'
        self.mock_github_instance.get_repo.side_effect = PyGithubErrorTypes.UnknownObjectException(status=404, data={}, headers=None)

        g = github_service_module.get_github_service()
        commits = github_service_module.get_repo_commits(g, 'user/nonexistent_repo')
        self.assertEqual(len(commits), 0)
        self.mock_logger.error.assert_any_call("Repository 'user/nonexistent_repo' not found.")

    def test_get_repo_commits_api_error(self):
        self.mock_getenv.return_value = 'test_pat'
        # Make get_repo itself raise the error, or the get_commits call on the repo object.
        # If get_repo succeeds but get_commits fails:
        mock_repo_obj = MagicMock()
        mock_repo_obj.get_commits.side_effect = PyGithubErrorTypes.GithubException(status=500, data={}, headers=None)
        self.mock_github_instance.get_repo.return_value = mock_repo_obj # get_repo is successful

        g = github_service_module.get_github_service()
        commits = github_service_module.get_repo_commits(g, 'user/repo1')
        self.assertEqual(len(commits), 0)
        self.mock_logger.error.assert_any_call("GitHub API error getting commits for user/repo1: 500 {}")

    def test_get_user_notifications_success(self):
        self.mock_getenv.return_value = 'test_pat'
        mock_notif_subject = MagicMock()
        mock_notif_subject.title = 'Test Notification'
        mock_notif_subject.type = 'Issue'
        mock_notif_subject.url = 'http://api.github.com/issues/1'

        mock_notif_repo = MagicMock()
        mock_notif_repo.full_name = 'user/repo_notif'

        mock_notif = MagicMock()
        mock_notif.id = '123'
        mock_notif.reason = 'subscribed'
        mock_notif.subject = mock_notif_subject
        mock_notif.repository = mock_notif_repo
        mock_notif.updated_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_notif.last_read_at = None
        mock_notif.unread = True

        self.mock_github_instance.get_notifications.return_value = [mock_notif]

        g = github_service_module.get_github_service()
        notifications = github_service_module.get_user_notifications(g)

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['id'], '123')
        self.assertEqual(notifications[0]['title'], 'Test Notification')
        self.mock_logger.info.assert_any_call("Fetching notifications (all: False, participating: False, since: N/A)..." )

    def test_get_user_notifications_with_since_iso_valid(self):
        self.mock_getenv.return_value = 'test_pat'
        since_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        since_iso = since_time.isoformat()

        self.mock_github_instance.get_notifications.return_value = []
        g = github_service_module.get_github_service()
        github_service_module.get_user_notifications(g, since_iso=since_iso)

        self.mock_github_instance.get_notifications.assert_called_once_with(all=False, participating=False, since=since_time)
        self.mock_logger.info.assert_any_call(f"Fetching notifications (all: False, participating: False, since: {since_iso})..." )

    def test_get_user_notifications_with_since_iso_invalid_format(self):
        self.mock_getenv.return_value = 'test_pat'
        self.mock_github_instance.get_notifications.return_value = []
        g = github_service_module.get_github_service()
        github_service_module.get_user_notifications(g, since_iso='invalid-date-format')

        self.mock_github_instance.get_notifications.assert_called_once_with(all=False, participating=False)
        self.mock_logger.warning.assert_any_call("Invalid 'since_iso' format: invalid-date-format. Should be ISO 8601. Fetching without time filter.")

    def test_get_user_notifications_api_error(self):
        self.mock_getenv.return_value = 'test_pat'
        self.mock_github_instance.get_notifications.side_effect = PyGithubErrorTypes.GithubException(status=500, data={}, headers=None)

        g = github_service_module.get_github_service()
        notifications = github_service_module.get_user_notifications(g)
        self.assertEqual(len(notifications), 0)
        self.mock_logger.error.assert_any_call("GitHub API error getting notifications: 500 {}")
    # --- End of newly added methods ---

if __name__ == '__main__':
    unittest.main()
