from datetime import date

from src.oracle.models import SpecialistProfile


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class GitHubScanner:
    """
    Scans a GitHub profile to extract specialist information.
    """

    def _fetch_github_data(self, username: str) -> dict:
        """
        A placeholder for a method that would call the GitHub API.
        This method is intended to be mocked during testing.
        """
        # This is mock data for the default, non-testing case.
        return {
            "github_username": username,
            "languages": ["Python", "JavaScript", "Go"],
            "skill_level": 8,
            "last_commit_date": date(2024, 7, 31),
        }

    def analyze(self, username: str) -> SpecialistProfile:
        """
        Analyzes a GitHub user's profile by fetching data and
        constructing a SpecialistProfile object.

        Args:
            username: The GitHub username to analyze.

        Returns:
            A SpecialistProfile object.

        Raises:
            GitHubAPIError: If the data fetching or profile creation fails.
        """
        try:
            user_data = self._fetch_github_data(username)
            return SpecialistProfile(**user_data)
        except Exception as e:
            # Re-raise exceptions as our custom error to simulate a failure boundary.
            raise GitHubAPIError(f"Failed to analyze profile for {username}: {e}") from e
