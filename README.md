# katana-ai

## Running Tests

This project uses `pytest` for running unit tests. Ensure you have `pytest` installed (it's included in the CI environment).

To run the tests locally:

1.  **Navigate to the project root directory.**
2.  **Set PYTHONPATH** (if your project structure requires it, like in this case where tests import from root modules):
    ```bash
    export PYTHONPATH=.
    ```
    Alternatively, you might install your project in editable mode if it's a package:
    ```bash
    # pip install -e . # If setup.py or pyproject.toml exists
    ```
3.  **Run pytest:**
    ```bash
    pytest
    ```
    You should see output indicating the number of tests run and their status. The CI pipeline also runs these tests automatically.

The tests cover various aspects of the application, including:
- Core functionality of different modules.
- Logging mechanisms to ensure messages are recorded correctly.