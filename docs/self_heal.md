# Katana Self-Healing Module

This document describes the functionality and usage of the Katana self-healing module.

## Overview

The self-healing module is designed to automatically diagnose and recover from errors and failures within the Katana application. It consists of three main components:

- **Diagnostics:** Monitors logs, checks module integrity, and detects anomalies.
- **Patcher:** Applies patches, restarts services, and rolls back changes.
- **CLI:** Provides a command-line interface for manual control and monitoring.

## Diagnostics

The diagnostics module provides the following functions:

- `calculate_hash(file_path)`: Calculates the SHA-256 hash of a file.
- `check_module_integrity(module_path, expected_hash)`: Checks the integrity of a module by comparing its hash with an expected hash.
- `analyze_logs(log_file)`: Analyzes a log file to find errors and anomalies.

## Patcher

The patcher module provides the following functions:

- `restart_service(service_name)`: Restarts a systemd service.
- `apply_patch(patch_file)`: Applies a git patch.
- `rollback_changes()`: Rolls back the latest git commit.
- `fetch_patch(patch_url)`: Fetches a patch from a URL.

## Git Integration

The git integration module provides the following function:

- `create_pull_request(title, body, head_branch, base_branch="main")`: Creates a pull request on GitHub.

## Command-Line Interface (CLI)

The CLI provides a way to manually trigger diagnostics and recovery actions.

### Diagnose

To run diagnostics, use the `diagnose` command:

```bash
python -m katana.self_heal.cli diagnose --log-file <path_to_log_file>
python -m katana.self_heal.cli diagnose --module-path <path_to_module> --expected-hash <hash>
```

### Patch

To run the patcher, use the `patch` command:

```bash
python -m katana.self_heal.cli patch --restart-service <service_name>
python -m katana.self_heal.cli patch --apply-patch <path_to_patch_file>
python -m katana.self_heal.cli patch --rollback
python -m katana.self_heal.cli patch --fetch-patch <url_to_patch>
```
