# katana_integrations/github_service.py

import os
from datetime import datetime, timedelta, timezone # Ensure timezone for UTC consistency

# PyGithub library - User needs to install this:
# pip install PyGithub
try:
    from github import Github
    from github.GithubException import GithubException, UnknownObjectException, BadCredentialsException
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False
    # This log will occur when github_service.py is imported if PyGithub is missing.
    # Note: if setup_logging() hasn't run, this might go to a default basicConfig.
    # It's logged here to ensure the message is captured if the module is imported early.
    import logging # Temporary import for early log
    logging.getLogger(__name__).critical("[GitHubService:CRITICAL_DEPENDENCY_ERROR] PyGithub library not found. Please run: pip install PyGithub")


from katana.logging_config import get_logger, setup_logging # setup_logging for __main__
import logging # For logger levels if needed

logger = get_logger(__name__)

# log_message_github function removed, using logger directly.

# --- Core Functions ---
def get_github_service():
    """
    Authenticates and returns the PyGithub Github client instance
    using a Personal Access Token (PAT) from GITHUB_PAT environment variable.
    """
    if not PYGITHUB_AVAILABLE:
        logger.critical("Cannot proceed: PyGithub library is not installed.")
        return None

    github_pat = os.getenv('GITHUB_PAT')
    if not github_pat:
        logger.critical("GITHUB_PAT environment variable not set. Cannot authenticate with GitHub.")
        logger.critical("Please create a PAT with appropriate scopes (e.g., repo, notifications, gist) and set it as GITHUB_PAT.")
        return None

    try:
        g = Github(github_pat)
        user = g.get_user() # Test authentication
        logger.info(f"Successfully authenticated with GitHub as user: {user.login}")
        return g
    except BadCredentialsException:
        logger.error("GitHub authentication failed: Bad credentials (invalid PAT?).")
        return None
    except GithubException as e: # Catch more specific PyGithub exceptions first
        logger.error(f"A GitHub API error occurred during authentication: {e.status} {e.data}")
        return None
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred during GitHub authentication: {e}")
        return None

def list_user_repos(g: Github, max_repos: int = 20):
    """Lists repositories for the authenticated user."""
    if not g: return []
    repos_info = []
    try:
        logger.info(f"Fetching up to {max_repos} repositories for authenticated user...")
        user = g.get_user()
        count = 0
        # Sort by 'pushed' for more recent activity, or 'updated'
        for repo in user.get_repos(sort="pushed", direction="desc"):
            if count >= max_repos:
                break
            repos_info.append({
                "full_name": repo.full_name, "name": repo.name, "description": repo.description,
                "url": repo.html_url, "language": repo.language, "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "last_updated": repo.updated_at.replace(tzinfo=timezone.utc).isoformat() if repo.updated_at else None, # Ensure UTC
                "is_fork": repo.fork, "is_private": repo.private
            })
            count += 1
        logger.info(f"Fetched {len(repos_info)} repositories.")
    except GithubException as e:
        logger.error(f"GitHub API error listing repositories: {e.status} {e.data}")
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
    return repos_info

def get_repo_commits(g: Github, repo_full_name: str, max_commits: int = 5):
    """Gets recent commits for a specific repository."""
    if not g: return []
    commits_info = []
    try:
        logger.info(f"Fetching last {max_commits} commits for repository: {repo_full_name}...")
        repo = g.get_repo(repo_full_name)
        commits_paginated_list = repo.get_commits()
        count = 0
        for commit in commits_paginated_list:
            if count >= max_commits:
                break
            commit_data = commit.commit
            author_date = commit_data.author.date.replace(tzinfo=timezone.utc).isoformat() if commit_data.author and commit_data.author.date else None
            commits_info.append({
                "sha": commit.sha,
                "author_name": commit_data.author.name if commit_data.author else "N/A",
                "author_email": commit_data.author.email if commit_data.author else "N/A",
                "date_utc": author_date,
                "message": commit_data.message, "url": commit.html_url
            })
            count += 1
        logger.info(f"Fetched {len(commits_info)} commits for {repo_full_name}.")
    except UnknownObjectException:
        logger.error(f"Repository '{repo_full_name}' not found.")
    except GithubException as e:
        logger.error(f"GitHub API error getting commits for {repo_full_name}: {e.status} {e.data}")
    except Exception as e:
        logger.error(f"Error getting commits for {repo_full_name}: {e}")
    return commits_info

def get_user_notifications(g: Github, since_iso: str = None, all_notifications: bool = False, participating: bool = False):
    """
    Gets notifications for the authenticated user.
    since_iso: An ISO 8601 string. Only notifications updated at or after this time are returned.
    """
    if not g: return []
    notifications_info = []
    since_dt = None
    if since_iso:
        try:
            since_dt = datetime.fromisoformat(since_iso.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid 'since_iso' format: {since_iso}. Should be ISO 8601. Fetching without time filter.")

    logger.info(f"Fetching notifications (all: {all_notifications}, participating: {participating}, since: {since_dt.isoformat() if since_dt else 'N/A'})...")
    try:
        # PyGithub's get_notifications takes 'all' and 'participating' booleans, and 'since' datetime object.
        # Need to ensure Github.NotSet is correctly handled or not needed if since_dt can be None
        notifications_call_args = {"all": all_notifications, "participating": participating}
        if since_dt:
            notifications_call_args["since"] = since_dt

        notifications = g.get_notifications(**notifications_call_args)

        for notif in notifications: # Iterate up to PyGithub's default pagination limit
            notifications_info.append({
                "id": notif.id, "reason": notif.reason, "title": notif.subject.title,
                "type": notif.subject.type, "url": notif.subject.url, # API URL
                "repository_full_name": notif.repository.full_name if notif.repository else "N/A",
                "updated_at_utc": notif.updated_at.replace(tzinfo=timezone.utc).isoformat() if notif.updated_at else None,
                "last_read_at_utc": notif.last_read_at.replace(tzinfo=timezone.utc).isoformat() if notif.last_read_at else None,
                "unread": notif.unread
            })
        logger.info(f"Fetched {len(notifications_info)} notifications.")
    except GithubException as e:
        logger.error(f"GitHub API error getting notifications: {e.status} {e.data}")
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
    return notifications_info

# --- Main Execution (Example Usage) ---
if __name__ == '__main__':
    # Setup logging for the example execution
    setup_logging(log_level=logging.INFO)
    # import traceback # For main example's error logging - logger.exception or logger.error with exc_info=True can be used instead

    logger.info("Starting GitHub Service example...")
    github_service = get_github_service()
    if github_service:
        logger.info("GitHub service obtained. Performing example actions...")
        my_repos = list_user_repos(github_service, max_repos=3)
        if my_repos:
            print("\n--- My Recent Repositories (up to 3) ---") # User-facing output
            for repo_data in my_repos:
                print(f"  Name: {repo_data['full_name']} (Lang: {repo_data['language']}, Last Updated: {repo_data['last_updated']})")
                if my_repos.index(repo_data) == 0:
                    repo_commits = get_repo_commits(github_service, repo_data['full_name'], max_commits=2)
                    if repo_commits:
                        print(f"    Recent Commits for {repo_data['full_name']} (up to 2):")
                        for commit_data in repo_commits:
                            print(f"      SHA: {commit_data['sha'][:7]}, Author: {commit_data['author_name']}, Date: {commit_data['date_utc']}") # User-facing output
                            print(f"      Msg: {commit_data['message'].splitlines()[0][:70]}...") # User-facing output
        else:
            logger.info("No repositories found or an error occurred.")

        print("\n--- My Unread Notifications (since 1 day ago) ---") # User-facing output
        since_yesterday_dt = datetime.now(timezone.utc) - timedelta(days=1)
        # Corrected call to get_user_notifications
        my_notifications = get_user_notifications(github_service, since_iso=since_yesterday_dt.isoformat(), all_notifications=False)
        if my_notifications:
            for notif_data in my_notifications[:3]: # Print max 3
                print(f"  Repo: {notif_data['repository_full_name']}, Title: {notif_data['title']} (Reason: {notif_data['reason']}, Unread: {notif_data['unread']})") # User-facing output
        else:
            logger.info("No unread notifications found since yesterday or an error occurred.")
    else:
        logger.critical("Could not initialize GitHub service. Exiting example.")
