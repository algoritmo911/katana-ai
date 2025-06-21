# Troubleshooting Common Issues

This document lists common issues encountered during development or setup of the Katana Bot, along with potential solutions and workarounds.

## Package Installation Problems

Some developers might experience issues when installing Python packages (e.g., `pyTelegramBotAPI`, `pytest`, `pytest-cov`, `flake8`, `black`, `isort`) using `pip`. These issues can manifest as:

*   **Timeout Errors**: `pip install` commands take too long and eventually fail due to network timeouts.
*   **Network Blockages**: Access to PyPI (the Python Package Index) or specific package repositories might be restricted by firewalls or network policies.

### Known Symptoms:

*   `pip install <package_name>` hangs indefinitely or for a very long time.
*   Error messages containing "Connection timed out", "Read timed out", "Network is unreachable", or similar.
*   SSL-related errors if custom SSL certificates are interfering.

### Potential Solutions and Workarounds:

1.  **Retry with Increased Timeout**:
    You can specify a longer timeout for `pip`:
    ```bash
    pip install --default-timeout=300 <package_name>
    ```
    Increase the value (in seconds) as needed.

2.  **Change Network Environment**:
    *   If possible, try switching to a different network (e.g., a mobile hotspot, a home network if you're on a corporate one, or vice-versa). This can help determine if the issue is network-specific.

3.  **Use a Proxy Server**:
    If your organization uses a proxy server for internet access, configure `pip` to use it:
    ```bash
    pip install --proxy [user:passwd@]proxy.server:port <package_name>
    ```
    You might also need to set environment variables `HTTP_PROXY` and `HTTPS_PROXY`.

4.  **Use a Different PyPI Mirror**:
    Sometimes the default PyPI index can be slow or temporarily unavailable. You can try using a regional mirror.
    ```bash
    pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple <package_name>
    ```
    (Example uses a mirror in China; find one appropriate for your region.)
    Remember to use `--trusted-host` if the mirror uses HTTP or has an SSL certificate `pip` doesn't trust by default.

5.  **Offline Installation (Manual Download)**:
    *   On a machine with internet access, download the required package wheels (`.whl` files) and their dependencies:
        ```bash
        pip download <package_name> -d /path/to/your/packages_directory
        ```
    *   Transfer these files to the target machine.
    *   Install from the local directory:
        ```bash
        pip install --no-index --find-links=/path/to/your/packages_directory <package_name>
        ```

6.  **Python Virtual Environments**:
    Always use virtual environments (e.g., `venv`, `conda`) to isolate project dependencies. This won't directly solve network issues but can prevent conflicts and make dependency management cleaner.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install <package_name>
    ```

7.  **Caching Pip Packages**:
    `pip` automatically caches packages. If a download was corrupted, clearing the cache might help, but this is less likely for persistent network issues.
    To clear the cache: `pip cache purge`.

## Mocking for CI/CD or Restricted Environments (Future Consideration)

As mentioned in feedback, if direct installation of dependencies like `httpx` or GUI/React components becomes problematic in certain environments (especially CI/CD pipelines or highly restricted development setups):

*   **Strategy**: We may need to implement mock objects or stubs for external services or complex UI components.
*   **Current Status**: The bot (`bot.py`) currently has minimal external dependencies beyond `pyTelegramBotAPI`. If new components are added that rely on services prone to installation/access issues (e.g., external APIs via `httpx`), we will update tests to use mocks.
*   **Developer Guidance**: Instructions will be provided on how to run tests in a "mocked" mode if this strategy is implemented.

## Contact & Feedback

If you encounter persistent issues not covered here, or if you find solutions that could benefit others, please:

*   **[Placeholder for contact method, e.g., "Update this document via a Pull Request", "Contact @your_team_lead on Telegram", or "Post in the #dev_support channel." ]**

We are actively working on ensuring a smooth development experience and appreciate your feedback on any blockers.
