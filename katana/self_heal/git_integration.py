import os
import requests
import json

def create_pull_request(title, body, head_branch, base_branch="main"):
    """Creates a pull request on GitHub."""
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        return None, "GITHUB_TOKEN environment variable not set."

    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return None, "GITHUB_REPOSITORY environment variable not set."

    url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch,
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json(), "Pull request created successfully."
    except requests.exceptions.RequestException as e:
        return None, f"Failed to create pull request: {e}"
