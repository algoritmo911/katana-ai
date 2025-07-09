# katana-ai

## Development Environment Setup

### Prerequisites
- Python 3.x
- pip

### 1. Clone the Repository
```bash
git clone <repository-url>
cd katana-ai
```

### 2. Install Dependencies
It's recommended to use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```
Install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Set Up Pre-commit Hooks
Pre-commit hooks help ensure code quality before you commit.
```bash
pip install pre-commit
pre-commit install
```
Now, `black` and `flake8` will run automatically on changed files before each commit.

### 4. Secrets and Environment Management with Doppler

This project uses [Doppler](https://doppler.com/) to manage API keys, environment variables, and other secrets. Doppler provides a central place to store secrets securely and inject them into the application environment at runtime.

**Local Development Setup with Doppler:**

1.  **Install Doppler CLI:**
    Follow the instructions on the [Doppler CLI installation guide](https://docs.doppler.com/docs/cli).

2.  **Login to Doppler:**
    ```bash
    doppler login
    ```
    This will open a browser window to authenticate your CLI with your Doppler account.

3.  **Set up the Project:**
    Navigate to the project's root directory in your terminal and run:
    ```bash
    doppler setup
    ```
    Follow the prompts to select the appropriate Doppler project (e.g., `katana-ai`) and configuration (e.g., `dev`). This will create a `.doppler` directory (which should be added to `.gitignore` if not already) linking your local project to the Doppler project.

4.  **Accessing Secrets:**
    Once set up, Doppler will automatically inject the secrets from your selected project and config when you run commands prefixed with `doppler run --`.

    Refer to the `.env.example` file for a list of environment variables the application expects (e.g., `TELEGRAM_BOT_TOKEN`, `WEBHOOK_URL`). These should be configured in your Doppler project. The `secrets.toml.example` file also shows examples of other secrets you might manage.

**Running the Application Locally with Doppler:**

To run the FastAPI application with secrets injected by Doppler:
```bash
doppler run -- uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
The `doppler run --` command ensures that `main.py` (and any other part of the application) can access the necessary environment variables like `TELEGRAM_BOT_TOKEN` and `WEBHOOK_URL` from Doppler.

If you are using `ngrok` for a public webhook URL during development:
1. Start ngrok: `ngrok http 8000`
2. Copy the public HTTPS URL provided by ngrok.
3. Update the `WEBHOOK_URL` secret in your Doppler `dev` config with this ngrok URL.
4. Restart the application using the `doppler run -- uvicorn ...` command above.

## Running Checks and Tests Locally

To ensure your code is clean, formatted, and all tests pass before pushing changes, use the `run_checks.sh` script. If tests require environment variables/secrets, they will be available if the test execution within the script (or the script itself) is eventually run via `doppler run --` (this is handled in CI).
For local execution, if your tests need secrets:
```bash
doppler run -- ./run_checks.sh
```
Otherwise, if tests don't yet need secrets:
```bash
./run_checks.sh
```
This script will:

```bash
./run_checks.sh
```
This script will:
1. Run `flake8` for linting.
2. Run `black` to format the code (it will reformat files if needed).
3. Run `pytest` with `coverage` to execute unit tests and report test coverage.

## Continuous Integration (CI) Pipeline

The project uses GitHub Actions for CI. The workflow is defined in `.github/workflows/main.yml`.
When you push changes to `main`, `setup/dev-infrastructure`, or create a pull request targeting `main`, the CI pipeline automatically:
1. Sets up a clean Python environment.
2. **Sets up Doppler CLI:** Initializes Doppler using a `DOPPLER_TOKEN` GitHub secret.
3. Installs all dependencies from `requirements.lock`.
4. Runs pre-commit checks.
5. **Runs script checks with Doppler:** Executes `./scripts/run_checks.sh` (which includes `pytest`) using `doppler run --`. This ensures that any tests requiring secrets have them available from Doppler.

If any of these steps fail, the CI build will be marked as failed.

## CI/CD Pipeline with Deployment and Doppler

This project uses GitHub Actions for Continuous Integration (CI) and Continuous Deployment (CD), with Doppler managing secrets. The primary workflow for this is defined in `.github/workflows/deploy.yml`.

### Workflow Overview (`deploy.yml`)

This workflow automates testing and deployment of the Telegram bot.

**Triggers:**
*   Push to `main` or `dev` branches.
*   Manual trigger via `workflow_dispatch`.

**Key Steps:**
1.  **Checkout Code.**
2.  **Set up Python.**
3.  **Set up Doppler CLI:** Initializes Doppler using the `DOPPLER_TOKEN` GitHub secret. This token allows the workflow to fetch the necessary secrets for the selected Doppler project and configuration.
4.  **Install Dependencies.**
5.  **Run Tests with Doppler:** Executes `pytest` using `doppler run -- pytest`, ensuring tests have access to secrets.
6.  **Deploy to Cloud with Doppler (Placeholder):**
    *   If tests pass, this step handles deployment.
    *   The deployment commands are run using `doppler run -- ...`, so deployment scripts can access necessary API keys and tokens (e.g., `RAILWAY_TOKEN`, `SSH_PRIVATE_KEY`) directly from Doppler as environment variables.
    *   The manual step of generating a `.env` file from GitHub secrets has been removed, as Doppler handles this securely.
7.  **Send Telegram Notification (Placeholder).**

### Doppler and GitHub Secrets for CI/CD

-   **`DOPPLER_TOKEN`**: This is the primary GitHub Secret you need to configure in your repository settings (`Settings > Secrets and variables > Actions`). This token is a Doppler Service Token with appropriate access to your Doppler project (e.g., `katana-ai`) and its configurations (e.g., `prd` for production, `dev` for development/staging).
-   All other secrets (like `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `RAILWAY_TOKEN`, etc.) should be managed within your Doppler project. The CI/CD pipeline will fetch them via the `DOPPLER_TOKEN`.
-   The `.github/workflows/doppler-sync.yml` workflow can be used to periodically check the connection to Doppler and list available secret names (not values) for verification.

**Migrating from individual GitHub Secrets to Doppler:**
If you previously had individual secrets like `TELEGRAM_BOT_TOKEN` defined in GitHub Secrets, you should:
1. Add these secrets to your Doppler project.
2. Remove the old individual GitHub Secrets (except for `DOPPLER_TOKEN`).
3. Ensure your `DOPPLER_TOKEN` has permissions to read these secrets.

### Local Testing of the Pipeline

While direct local execution of GitHub Actions workflows can be complex, you can simulate parts of it:

1.  **Run Checks Script:** Always run `./run_checks.sh` locally before pushing to ensure tests and linting pass. This script covers a significant portion of what the CI part of the `deploy.yml` workflow does.
2.  **Test Branch:** Push your changes to a feature branch (e.g., `feat/test-cicd`) that is *not* `main` or `dev`. Then, create a Pull Request targeting `dev` or `main`. This will trigger the `main.yml` workflow (if configured for PRs) or you can temporarily modify `deploy.yml` to trigger on your feature branch for testing purposes.
3.  **`act` (Advanced):** For more comprehensive local testing of GitHub Actions, you can use a tool like [`act`](https://github.com/nektos/act). It allows you to run your GitHub Actions workflows locally using Docker. Installation and usage instructions are available on its GitHub page. This requires Docker to be installed and running.
    ```bash
    # Example (after installing act):
    # Dry run
    # act -n
    # Run the default event (push)
    # act
    # Run a specific job from a workflow
    # act -j build -W .github/workflows/deploy.yml
    ```

## Guidelines for Writing New Tests

*   **New Features, New Tests:** Every new feature, component, or significant piece of logic should have corresponding unit tests.
*   **Test Public Interfaces:** Focus your tests on the public methods and interfaces of your modules and classes. Test the contract, not the implementation details.
*   **Cover Critical Paths & Edge Cases:** Ensure your tests cover:
    *   Happy paths (expected, correct usage).
    *   Error conditions (e.g., invalid input, missing data).
    *   Edge cases (e.g., empty inputs, zero values, boundary conditions).
*   **Keep Tests Independent:** Each test case should be independent and not rely on the state or outcome of other tests.
*   **Update Tests with Code:** If you refactor or change existing code, ensure you update the corresponding tests to reflect these changes. Outdated tests can be misleading.
*   **Aim for Readability:** Write clear and understandable test code. Good test names and well-structured assertions help.

## Troubleshooting

For common issues and their solutions, please refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Common Issues & Solutions (Placeholder)

*(This section can be expanded as common issues are identified with local setup or testing.)*

*   **ModuleNotFoundError:** If you encounter `ModuleNotFoundError` when running tests, ensure your `PYTHONPATH` is correctly set to include the project's root directory (e.g., `export PYTHONPATH=.` from the project root) or that you have activated your virtual environment.
*   **Dependency Issues:** Ensure all development dependencies (like `pytest`, `flake8`, `black`) are installed in your active virtual environment using `pip install -r requirements.txt`.