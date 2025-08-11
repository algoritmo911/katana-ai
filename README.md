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

### 4. Environment Variables (If Applicable)
If the project requires specific environment variables for configuration (e.g., API keys, database URLs):
- Create a `.env` file in the project root.
- You can use `.env.example` as a template if it exists.
- **Note:** `.env` files should be added to `.gitignore` to avoid committing secrets.
  (At the moment, no specific environment variables are defined for this project).

### 5. API Keys and Secrets Management (`secrets.toml`)

For integrations with external services that require API keys or other secrets (like Coinbase for authenticated actions in the future), this project uses a `secrets.toml` file.

-   **Template:** A template file `secrets.toml.example` is provided in the repository. It shows the expected structure for your secrets.
-   **Local Setup:** To use services requiring secrets:
    1.  Copy `secrets.toml.example` to a new file named `secrets.toml` in the project root.
    2.  Edit `secrets.toml` and fill in your actual API keys and other secret values.
-   **Security:**
    -   The `secrets.toml` file is **explicitly ignored by Git** (via `.gitignore`).
    -   **DO NOT COMMIT YOUR ACTUAL `secrets.toml` FILE OR YOUR SECRETS TO THE REPOSITORY.**
    -   Currently, only unauthenticated API endpoints (like Coinbase spot prices) are used, so `secrets.toml` is for future-proofing authenticated requests.

## Legion Architecture: Orchestrator and Workers

The Katana AI project now includes a distributed agent architecture named "Legion". This system is designed to handle complex tasks by breaking them down into smaller pieces and distributing them among specialized worker agents.

### Core Components

1.  **Task Queue (`katana/task_queue`)**: The communication backbone of the system. It uses Redis as a message broker to queue tasks. All tasks are represented by a `Task` object and managed by the `TaskQueueService`.

2.  **OrchestratorAgent (`katana/orchestrator_agent.py`)**: The "brain" of the system. When a complex query is received, the orchestrator:
    -   Decomposes the query into a series of atomic sub-tasks.
    -   Dispatches these sub-tasks to the task queue.
    -   Waits for all sub-tasks to be completed by the workers.
    -   Collects the results.
    -   Synthesizes the results into a single, coherent final answer.

3.  **Workers (`worker.py`)**: These are standalone, specialized processes that listen for specific types of tasks on the queue. Each worker has a set of "executors" for the tasks it can handle (e.g., `web_search`, `financial_data_api`).
    -   When a worker picks up a task, it executes the corresponding function.
    -   Upon completion, it stores the result back into the task object in the broker.

### How to Run the System Locally

To run the full Legion system, you need at least two processes running: the main FastAPI application and one or more worker processes.

**1. Start Redis:**
The system requires a running Redis instance. Use the provided Docker Compose file to start one easily.
```bash
docker compose up -d redis
```

**2. Start the Main Application:**
This runs the FastAPI server, which includes the Telegram bot integration and the `OrchestratorAgent`.
```bash
# In your activated virtual environment
uvicorn main:app --reload
```

**3. Start the Worker(s):**
In a separate terminal, run the `worker.py` script. You can run multiple instances of this script to scale up the processing power.
```bash
# In another terminal, with the virtual environment activated
PYTHONPATH=. python worker.py
```
The worker process will connect to Redis and start listening for jobs dispatched by the Orchestrator.

## Running Checks and Tests Locally

To ensure your code is clean, formatted, and all tests pass before pushing changes, use the `run_checks.sh` script:

```bash
./run_checks.sh
```
This script will:
1. Run `flake8` for linting.
2. Run `black` to format the code (it will reformat files if needed).
3. Run `pytest` with `coverage` to execute unit tests and report test coverage.

## Continuous Integration (CI) Pipeline

The project uses GitHub Actions for CI. The workflow is defined in `.github/workflows/main.yml`.
When you push changes to `main` or create a pull request targeting `main`, the CI pipeline automatically:
1. Sets up a clean Python environment.
2. Installs all dependencies from `requirements.txt`.
3. Runs the `./run_checks.sh` script, which includes:
    - Linting with `flake8`.
    - Formatting checks with `black`.
    - Unit tests with `pytest` and coverage reporting.

If any of these steps fail, a CI build will be marked as failed, helping to catch issues early.

## CI/CD Pipeline with Deployment

This project uses GitHub Actions for Continuous Integration (CI) and Continuous Deployment (CD). The primary workflow for this is defined in `.github/workflows/deploy.yml`.

### Workflow Overview (`deploy.yml`)

This workflow automates testing and deployment of the Telegram bot.

**Triggers:**
*   Push to `main` branch.
*   Push to `dev` branch.
*   Manual trigger via `workflow_dispatch` from the GitHub Actions UI.

**Key Steps:**
1.  **Checkout Code:** Fetches the latest version of your repository.
2.  **Set up Python:** Configures the specified Python version (e.g., 3.10).
3.  **Install Dependencies:** Installs all required packages from `requirements.txt`.
4.  **Run Tests:** Executes the test suite using `pytest`. All tests must pass for the workflow to proceed to deployment.
5.  **Generate `.env` File (Simulated in CI):**
    *   During the CI/CD run, a `.env` file is generated using secrets stored in GitHub. This step ensures that sensitive information like API tokens are not hardcoded in the repository but are available to the application at runtime.
    *   The actual deployment environment (e.g., Railway, Render, VPS) will need these environment variables set up.
6.  **Deploy to Cloud (Placeholder):**
    *   If tests pass, this step handles the deployment. The actual deployment commands will depend on the chosen hosting platform (e.g., Railway, Render, or a custom script for a VPS).
    *   This step is currently a placeholder and needs to be configured with actual deployment logic.
7.  **Send Telegram Notification (Placeholder):**
    *   An optional step to send a notification (e.g., via a Telegram message) about the status (success or failure) of the deployment.

### GitHub Secrets for CI/CD

The `deploy.yml` workflow relies on GitHub Secrets to securely manage sensitive information like API keys and deployment tokens. These secrets are encrypted and can only be used by GitHub Actions.

**Required Secrets (add these in your GitHub repository settings under `Settings > Secrets and variables > Actions`):**
*   `TELEGRAM_BOT_TOKEN`: Your Telegram bot's API token.
*   `OPENAI_API_KEY`: Your OpenAI API key (if used by the bot).
*   `RAILWAY_TOKEN`: Your Railway API token (if deploying to Railway).
*   `SSH_PRIVATE_KEY`: Your SSH private key for deploying to a VPS (if using SCP/SSH). *Ensure you store the private key securely and configure the corresponding public key on your server.*
*   *(Add any other secrets your bot or deployment process might need).*

**How to Add New Secrets:**
1.  Go to your GitHub repository.
2.  Click on "Settings".
3.  In the left sidebar, navigate to "Secrets and variables" > "Actions".
4.  Click the "New repository secret" button.
5.  Enter the name of the secret (e.g., `TELEGRAM_BOT_TOKEN`) and its value.
6.  Click "Add secret".

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