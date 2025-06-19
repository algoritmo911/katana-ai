# Katana Integrations Package

This package contains Python modules designed to integrate Katana with various external services for data harvesting and interaction. The primary goal is to gather contextual information to build Katana's memory and awareness.

## Modules

### 1. Gmail Service (`gmail_service.py`)

**Purpose**:
Connects to the Gmail API to fetch and parse email data. This can be used to identify service registrations, track communications, and extract relevant text for Katana's memory.

**Dependencies**:
Install the necessary Google API client libraries:
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

**Authentication**:
This module uses OAuth 2.0 to access Gmail data.
1.  **Enable Gmail API**: Ensure the Gmail API is enabled for your project in the Google Cloud Console.
2.  **Create OAuth 2.0 Credentials**:
    *   Go to the "Credentials" page in Google Cloud Console.
    *   Create new credentials of type "OAuth client ID".
    *   Select "Desktop app" as the application type.
    *   Download the JSON file containing your client ID and client secret.
3.  **Save `credentials.json`**: Rename the downloaded JSON file to `credentials.json` and place it in the `katana_integrations/` directory (i.e., alongside `gmail_service.py`). The script defines `CREDENTIALS_JSON_PATH = _SCRIPT_DIR / 'credentials.json'`.
4.  **First Run & Authorization**:
    *   When `gmail_service.py` (or a script using its `get_gmail_service()` function) is run for the first time, it will attempt to open a web browser to guide you through the Google OAuth 2.0 consent screen.
    *   You will need to authorize the application to access your Gmail data (with the read-only scope defined in the script).
    *   Upon successful authorization, a `token.json` file will be automatically created in the `katana_integrations/` directory. This file stores your access and refresh tokens, allowing the script to authenticate on subsequent runs without requiring browser interaction (unless the token is revoked or expires without a refresh token).
    *   **Important**: Keep `token.json` secure, as it grants access to your Gmail account. Do not commit it to version control if this is a shared project. Add `token.json` to your `.gitignore` file.

**Usage**:
See the `if __name__ == '__main__':` block in `gmail_service.py` for an example of how to initialize the service and fetch emails. The script expects `credentials.json` and will create `token.json` in the same directory as `gmail_service.py`.

### 2. GitHub Service (`github_service.py`)

**Purpose**:
Connects to the GitHub API to fetch information about repositories, commits, notifications, and other user activities. This helps Katana understand project context and development history.

**Dependencies**:
Install the PyGithub library:
```bash
pip install PyGithub
```

**Authentication**:
This module uses a GitHub Personal Access Token (PAT) for authentication.
1.  **Generate a PAT**:
    *   Go to your GitHub settings: Developer settings -> Personal access tokens (Tokens (classic) or Fine-grained tokens).
    *   Generate a new token.
    *   Grant appropriate scopes. For the current functionality, you might need:
        *   `repo` (to access private and public repository data)
        *   `notifications` (to read notifications)
        *   `gist` (if you plan to interact with gists)
        *   `user` (to read user profile information)
    *   Copy the generated token immediately. You will not be able to see it again.
2.  **Set Environment Variable**:
    Set the `GITHUB_PAT` environment variable to your generated token:
    ```bash
    export GITHUB_PAT="your_github_personal_access_token_here"
    ```
    It's recommended to add this to your shell's profile (e.g., `~/.zshrc`, `~/.bashrc`) for persistence across sessions.

**Usage**:
See the `if __name__ == '__main__':` block in `github_service.py` for an example of how to initialize the service and fetch repository, commit, and notification data.

## General Notes
- These modules are intended to be used as part of the larger Katana ecosystem. The data harvested is meant to be processed and stored in Katana's memory.
- Ensure all dependencies are installed in your Python environment.
- Manage your credentials (`credentials.json`, `token.json`, `GITHUB_PAT`) securely and avoid committing them to version control.