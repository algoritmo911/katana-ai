# katana-ai

## Local Development Checks

To ensure code quality and consistency before committing, you can run the following checks locally. These are the same checks performed by the CI pipeline.

### Running Tests

This project uses `pytest` for running unit tests.

1.  **Navigate to the project root directory.**
2.  **(Optional but recommended for consistency with CI) Set PYTHONPATH:**
    Our tests might rely on discovering modules from the project root. To ensure consistent behavior with how Python might see your modules during CI or if your project isn't installed as a package, you can set `PYTHONPATH`:
    ```bash
    export PYTHONPATH=.
    ```
    Alternatively, if your project is structured as an installable package, you might run:
    ```bash
    # pip install -e . # If you have a setup.py or pyproject.toml
    ```
3.  **Run pytest:**
    To run all tests within the `tests/` directory:
    ```bash
    pytest tests/
    ```
    Or, if using the `PYTHONPATH` method above, simply:
    ```bash
    pytest
    ```
    You should see output indicating the number of tests run and their status.

### Linting with flake8

To check your code for style issues and potential errors using `flake8`:
```bash
flake8 .
```
Review any reported errors or warnings.

### Checking Formatting with black

To check if your code adheres to the `black` code formatting standards without modifying files:
```bash
black --check .
```
If `black` reports that files would be reformatted, you can apply the formatting by running:
```bash
black .
```