# Troubleshooting Guide

This document provides solutions to common problems encountered during setup or development.

## Pre-commit Hooks

### `pre-commit` command not found
- **Symptom:** Shell reports `pre-commit: command not found`.
- **Solution:** Ensure `pre-commit` is installed and your environment's `bin` directory is in your `PATH`.
  ```bash
  pip install pre-commit
  ```
  If you are using a virtual environment, make sure it's activated.

### Hooks are not running
- **Symptom:** Git commits succeed without `black` or `flake8` running.
- **Solution:** Ensure pre-commit hooks are installed in your local repository.
  ```bash
  pre-commit install
  ```

## Running Checks (`run_checks.sh`)

### `./run_checks.sh: Permission denied`
- **Symptom:** Attempting to run `./run_checks.sh` results in a permission error.
- **Solution:** The script needs execute permissions.
  ```bash
  chmod +x run_checks.sh
  ```

### `ModuleNotFoundError` or Import Errors
- **Symptom:** `flake8`, `black`, `pytest`, or `coverage` report errors like `ModuleNotFoundError: No module named 'your_module'`.
- **Solutions:**
    1. **Activate Virtual Environment:** Make sure your project's virtual environment (e.g., `venv`) is activated.
       ```bash
       source venv/bin/activate  # For Linux/macOS
       # venv\Scripts\activate  # For Windows
       ```
    2. **Install Dependencies:** Ensure all dependencies are installed from `requirements.txt`.
       ```bash
       pip install -r requirements.txt
       ```
    3. **PYTHONPATH:** For some project structures, you might need to set the `PYTHONPATH`. From the project root:
       ```bash
       export PYTHONPATH=.
       ```
       Consider if your project structure requires this or if imports can be made relative/absolute without it.

### `black` reports "files would be reformatted" but doesn't reformat them in `run_checks.sh`
- **Symptom:** The `run_checks.sh` script's `black .` command (if not `black --check .`) should reformat files, but they remain unchanged.
- **Solution:** The `run_checks.sh` script was initially set up with `black .` which *should* reformat. If it's not, ensure:
    - No other processes are locking the files.
    - You have write permissions to the files.
    - The version of `black` is consistent with the one used in pre-commit hooks if applicable. The script should ideally directly apply formatting.

## CI Pipeline Failures

### Flake8 or Black Failures in CI
- **Symptom:** The GitHub Actions CI build fails on linting or formatting steps.
- **Solution:**
    1. Run `./run_checks.sh` locally to identify and fix the issues.
    2. Ensure your code is formatted with `black .` locally.
    3. Address all `flake8` errors.
    4. Commit the changes and push again.

### Test Failures in CI
- **Symptom:** The GitHub Actions CI build fails on the `pytest` step.
- **Solution:**
    1. Run `pytest` locally (ideally via `./run_checks.sh`) to reproduce and debug the failing tests.
    2. Ensure all tests pass locally before pushing.

---

*If you encounter an issue not listed here, please consider adding it to this guide after finding a solution.*
