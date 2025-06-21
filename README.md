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

If any of these steps fail, the CI build will be marked as failed, helping to catch issues early.

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