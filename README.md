# katana-ai

## Local Development Checks & Writing Tests

To ensure code quality, consistency, and stability before committing, please run the following checks locally. These are generally the same checks performed by the CI pipeline.

### Running Local Checks Before Pushing

Always perform these checks before pushing your changes:

1.  **Run Unit Tests with pytest:**
    ```bash
    # Ensure your PYTHONPATH is set if needed, e.g., from the project root:
    # export PYTHONPATH=.
    pytest tests/
    ```
    All tests should pass.

2.  **Lint with flake8:**
    ```bash
    flake8 .
    ```
    Address any reported errors or significant warnings.

3.  **Check Formatting with black:**
    ```bash
    black --check .
    ```
    If `black` reports that files would be reformatted, apply the formatting by running:
    ```bash
    black .
    ```

### Guidelines for Writing New Tests

As the project evolves, maintaining good test coverage is crucial.

*   **New Features, New Tests:** Every new feature, component, or significant piece of logic should have corresponding unit tests.
*   **Test Public Interfaces:** Focus your tests on the public methods and interfaces of your modules and classes. Test the contract, not the implementation details.
*   **Cover Critical Paths & Edge Cases:** Ensure your tests cover:
    *   Happy paths (expected, correct usage).
    *   Error conditions (e.g., invalid input, missing data).
    *   Edge cases (e.g., empty inputs, zero values, boundary conditions).
*   **Keep Tests Independent:** Each test case should be independent and not rely on the state or outcome of other tests.
*   **Update Tests with Code:** If you refactor or change existing code, ensure you update the corresponding tests to reflect these changes. Outdated tests can be misleading.
*   **Aim for Readability:** Write clear and understandable test code. Good test names and well-structured assertions help.

### Common Issues & Solutions (Placeholder)

*(This section can be expanded as common issues are identified with local setup or testing.)*

*   **ModuleNotFoundError:** If you encounter `ModuleNotFoundError` when running tests, ensure your `PYTHONPATH` is correctly set to include the project's root directory (e.g., `export PYTHONPATH=.` from the project root).
*   **Dependency Issues:** Ensure all development dependencies (like `pytest`, `flake8`, `black`) are installed in your environment.