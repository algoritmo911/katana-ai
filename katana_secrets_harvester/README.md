# Katana Secrets Harvester (Stage 1: Google Keep)

## Purpose
The Katana Secrets Harvester is a Python utility designed to automatically collect API keys, tokens, and other secrets from Google Keep notes. It specifically looks for notes tagged with a designated label (default: "api") and parses their content for key-value pairs. The collected secrets are then saved into a local JSON file (`secrets_temp.json`).

This tool helps in managing frequently changing or temporary secrets by centralizing their temporary storage in Google Keep notes and providing an automated way to gather them for use in development or other processes.

## Features
- Secure login to Google Keep (supports App Passwords for 2FA-enabled accounts).
- Finds notes based on a specific label (default: "api").
- Parses key-value pairs from the text content of notes (format: `KEY=VALUE`).
- Ignores lines starting with `#` (comments).
- Aggregates all found keys from multiple notes.
- Saves the collected secrets into a `secrets_temp.json` file.
- Automatically backs up any existing `secrets_temp.json` file before overwriting (e.g., to `secrets_temp_{timestamp}.json.bak`).

## Setup and Installation

1.  **Prerequisites**:
    *   Python 3.7+
    *   `pip` (Python package installer)

2.  **Install Dependencies**:
    The primary dependency is `gkeepapi` for interacting with Google Keep.
    ```bash
    pip install gkeepapi
    ```

3.  **Google Account Configuration**:
    *   **Standard Accounts**: Use your regular Google account email and password.
    *   **Accounts with 2-Step Verification (2FA/MFA)**: You **must** generate and use an "App Password" for this script. Google will block login attempts from less secure apps if you use your regular password with 2FA enabled.
        *   Go to your Google Account settings.
        *   Navigate to "Security".
        *   Under "Signing in to Google," find "App passwords." (You might need to enable 2-Step Verification first if you haven't).
        *   Generate a new app password (e.g., select "Mail" or "Other (Custom name)" for the app, give it a name like "KatanaHarvester").
        *   Use this generated 16-character app password as the password for this script.

4.  **Environment Variables**:
    The script requires your Google Keep credentials to be set as environment variables for security (do not hardcode them in the script):
    ```bash
    export GKEEP_USERNAME="your_google_email@example.com"
    export GKEEP_PASSWORD="your_gkeep_password_or_app_password"
    ```
    You can add these to your shell's profile file (e.g., `~/.bashrc`, `~/.zshrc`) or set them for the current session.

5.  **Google Keep Notes Preparation**:
    *   Create notes in Google Keep that contain the API keys or secrets you want to harvest.
    *   Each secret should be on a new line in the format `KEY=VALUE`.
        ```
        OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        DATABASE_URL=postgres://user:pass@host:port/dbname
        # This is a comment, will be ignored
        ANOTHER_SECRET=some_other_value
        ```
    *   Apply a specific label to these notes. By default, the script looks for the label named "api". You can change this by modifying the `DEFAULT_API_LABEL` constant in `harvester.py` or by passing the label name as an argument if the script is extended to support that.

## Usage

Once setup is complete, run the script from within the `katana_secrets_harvester` directory:

```bash
python harvester.py
```

The script will:
1.  Attempt to log in to Google Keep using the provided environment variables.
2.  Search for notes with the "api" label.
3.  Parse keys from these notes.
4.  Save all collected keys into `secrets_temp.json` in the `katana_secrets_harvester` directory.
5.  If `secrets_temp.json` already exists, it will be backed up (e.g., `secrets_temp_20231027_123045.json.bak`) before being overwritten.

Check the console output for logs of the process, including successful operations, warnings, or errors.

## Running Tests
Unit tests are provided in the `tests/` directory. To run them:
1. Ensure you are in the `katana_secrets_harvester` parent directory (i.e., the directory *containing* the `katana_secrets_harvester` project folder, or ensure `katana_secrets_harvester` project is in your PYTHONPATH).
2. Run the unittest discovery mechanism:
   ```bash
   python -m unittest discover -s katana_secrets_harvester/tests -p "test_*.py"
   ```
   Or, if inside the `katana_secrets_harvester` directory itself:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
   Or directly run the test file:
   ```bash
   python tests/test_harvester.py
   ```

## Future Enhancements (Stage 2+)
- Integration with cloud secret managers (e.g., Google Secret Manager, HashiCorp Vault) to push these temporary secrets.
- Synchronization with iCloud Keychain notes.
- More sophisticated parsing rules.
- GUI or web interface.