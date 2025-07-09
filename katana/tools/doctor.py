# This module will contain the logic for the 'katana doctor' command.
import argparse
import json
import os
import shutil
import subprocess
import time
import importlib
from pathlib import Path

# Configuration file path
# Assuming doctor.py is in katana/tools/doctor.py, to get to project root:
# Path(__file__).resolve().parent -> tools
# Path(__file__).resolve().parent.parent -> katana
# Path(__file__).resolve().parent.parent.parent -> project root
CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "katana_dependencies.json"
HUGGINGFACE_CACHE_DIR = Path(os.path.expanduser("~/.cache/huggingface"))

def _log_check(report, check_type, name, status, message, details=None):
    """Helper to add a check result to the report."""
    check_entry = {
        "type": check_type,
        "name": name,
        "status": status, # "OK", "FAIL", "WARN", "INFO"
        "message": message,
    }
    if details:
        check_entry["details"] = details
    report["checks"].append(check_entry)
    print(f"[{status}] {check_type} '{name}': {message}")

def _load_config():
    """Loads the dependency configuration."""
    if not CONFIG_FILE.exists():
        # This case should ideally be handled by a default config or an error
        print(f"Error: Configuration file {CONFIG_FILE} not found.")
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def check_libraries(report, config, auto_fix=False):
    """Checks for mandatory libraries and attempts to install them if auto_fix is True."""
    print("\n--- Checking Libraries ---")
    if not config or "mandatory" not in config:
        _log_check(report, "library_config", "mandatory_list", "FAIL", "Mandatory library list not found in config.")
        return

    for lib_name in config["mandatory"]:
        try:
            importlib.import_module(lib_name)
            _log_check(report, "library", lib_name, "OK", f"Library '{lib_name}' is installed.")
        except ImportError:
            if auto_fix:
                _log_check(report, "library", lib_name, "WARN", f"Library '{lib_name}' not found. Attempting to install...")
                try:
                    subprocess.run(['pip', 'install', lib_name], check=True, capture_output=True, text=True)
                    _log_check(report, "library_fix", lib_name, "OK", f"Successfully installed '{lib_name}'.")
                    # Verify import after install
                    importlib.import_module(lib_name)
                except subprocess.CalledProcessError as e:
                    _log_check(report, "library_fix", lib_name, "FAIL", f"Failed to install '{lib_name}'. Error: {e.stderr}")
                except ImportError:
                     _log_check(report, "library_fix", lib_name, "FAIL", f"Still unable to import '{lib_name}' after attempting install.")
            else:
                _log_check(report, "library", lib_name, "FAIL", f"Library '{lib_name}' not found. Run with --auto-fix to attempt installation.")

def check_huggingface_models(report, config):
    """Checks for specified HuggingFace models (conceptual check, actual download is by transformers)."""
    print("\n--- Checking HuggingFace Models ---")
    if not config or "models" not in config:
        _log_check(report, "model_config", "models_list", "WARN", "HuggingFace models list not found in config. Skipping check.")
        return

    # This is a conceptual check. Actual model availability depends on transformers library.
    # We can check if the model folders exist in the cache, but this is not foolproof.
    for model_name in config["models"]:
        # A more robust check would involve trying to load the model with transformers,
        # but that might be too slow or resource-intensive for a quick doctor check.
        # For now, we'll just log that they are configured.
        _log_check(report, "huggingface_model", model_name, "INFO", f"Configured model: '{model_name}'. Availability depends on transformers library and network access.")
        # Example of a cache check (can be very complex due to versioning/sharding):
        # model_cache_path = HUGGINGFACE_CACHE_DIR / "hub" / f"models--{model_name.replace('/', '--')}"
        # if model_cache_path.exists():
        #     _log_check(report, "huggingface_model_cache", model_name, "INFO", f"Model '{model_name}' seems to have cached files.")
        # else:
        #     _log_check(report, "huggingface_model_cache", model_name, "WARN", f"No cache found for '{model_name}'. May need to be downloaded on first use.")


def check_env_variables(report, config):
    """Checks for required environment variables."""
    print("\n--- Checking Environment Variables ---")
    if not config or "env_variables" not in config:
        _log_check(report, "env_config", "env_variables_list", "WARN", "Environment variables list not found in config. Skipping check.")
        return

    for var_name in config["env_variables"]:
        if var_name in os.environ:
            _log_check(report, "env_variable", var_name, "OK", f"Environment variable '{var_name}' is set.")
        else:
            _log_check(report, "env_variable", var_name, "FAIL", f"Environment variable '{var_name}' is not set. Example: export {var_name}=\"your_value\"")

def check_disk_space(report, config):
    """Checks for sufficient disk space in specified paths."""
    print("\n--- Checking Disk Space ---")
    if not config or "disk_space_paths" not in config:
        _log_check(report, "disk_space_config", "disk_space_paths_list", "WARN", "Disk space paths list not found in config. Skipping check.")
        return

    for item in config["disk_space_paths"]:
        path_str = item["path"]
        min_gb = item["min_gb"]

        path = Path(os.path.expanduser(path_str)).resolve()

        if not path.exists():
            # If path doesn't exist, try to check parent for mount point
            parent_path = path.parent
            while not parent_path.exists() and parent_path != parent_path.parent:
                parent_path = parent_path.parent
            if not parent_path.exists():
                 _log_check(report, "disk_space", str(path), "WARN", f"Path '{path}' or its mount point parent does not exist. Cannot check disk space.")
                 continue
            usage_path = parent_path # Check usage of the mount point
        else:
            usage_path = path

        try:
            usage = shutil.disk_usage(str(usage_path))
            free_gb = usage.free / (1024**3)
            if free_gb >= min_gb:
                _log_check(report, "disk_space", str(path), "OK", f"Available space: {free_gb:.2f}GB (min: {min_gb}GB) at '{usage_path}'.")
            else:
                _log_check(report, "disk_space", str(path), "WARN", f"Low disk space: {free_gb:.2f}GB available (min: {min_gb}GB) at '{usage_path}'.")
        except FileNotFoundError:
             _log_check(report, "disk_space", str(path), "WARN", f"Path '{usage_path}' not found for disk usage check.")
        except Exception as e:
            _log_check(report, "disk_space", str(path), "FAIL", f"Could not check disk space for '{usage_path}'. Error: {e}")


def clear_huggingface_cache(report):
    """Clears the HuggingFace cache directory with user confirmation."""
    print("\n--- Clearing HuggingFace Cache ---")
    if not HUGGINGFACE_CACHE_DIR.exists():
        _log_check(report, "cache_clear", str(HUGGINGFACE_CACHE_DIR), "INFO", "HuggingFace cache directory does not exist. Nothing to clear.")
        print("HuggingFace cache directory does not exist. Nothing to clear.")
        return

    print(f"WARNING: This will delete the directory: {HUGGINGFACE_CACHE_DIR}")
    confirm = input("Are you sure you want to continue? (yes/no): ").strip().lower()
    if confirm == 'yes':
        try:
            shutil.rmtree(HUGGINGFACE_CACHE_DIR)
            _log_check(report, "cache_clear", str(HUGGINGFACE_CACHE_DIR), "OK", "HuggingFace cache cleared successfully.")
            print("HuggingFace cache cleared successfully.")
        except Exception as e:
            _log_check(report, "cache_clear", str(HUGGINGFACE_CACHE_DIR), "FAIL", f"Failed to clear HuggingFace cache. Error: {e}")
            print(f"Failed to clear HuggingFace cache. Error: {e}")
    else:
        _log_check(report, "cache_clear", str(HUGGINGFACE_CACHE_DIR), "INFO", "Cache clearing aborted by user.")
        print("Cache clearing aborted.")


def run_doctor(auto_fix=False, clear_cache_flag=False):
    """
    Main function for the doctor tool.
    """
    start_time = time.time()
    report = {
        "timestamp": start_time,
        "katana_version": "0.1.0", # Placeholder, could be dynamic
        "status_summary": "", # Will be "OK" or "ISSUES_FOUND"
        "checks": []
    }

    print("🩺 Running Katana Doctor...")

    config = _load_config()
    if not config:
        _log_check(report, "configuration", "katana_dependencies.json", "FAIL", f"Could not load {CONFIG_FILE}. Many checks will be skipped.")
        # Fallback or default config could be loaded here if desired
    else:
        _log_check(report, "configuration", "katana_dependencies.json", "OK", f"Successfully loaded {CONFIG_FILE}.")


    if clear_cache_flag:
        clear_huggingface_cache(report)
        # Decide if other checks should run after cache clearing or if it's a standalone op
        # For now, let's assume it's a standalone op if this flag is true
        # logs_dir = Path("logs")
        # logs_dir.mkdir(exist_ok=True)
        # report_path = logs_dir / f"doctor_report_cache_clear_{int(start_time)}.json"

    else:
        # Perform all checks only if not just clearing cache
        if config: # Only run these if config was loaded
            check_libraries(report, config, auto_fix)
            check_huggingface_models(report, config)
            check_env_variables(report, config)
            check_disk_space(report, config)

    # Determine overall status
    if any(check["status"] in ["FAIL", "WARN"] for check in report["checks"]):
        report["status_summary"] = "ISSUES_FOUND"
    else:
        report["status_summary"] = "OK"

    print(f"\n🩺 Katana Doctor finished. Overall status: {report['status_summary']}")

    # Create logs directory if it doesn't exist
    # Ensure logs_dir is defined, Path from pathlib is used
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Save report
    report_filename = f"doctor_report_{int(start_time)}.json"
    report_path = logs_dir / report_filename
    try:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        print(f"Doctor report saved to {report_path}")
    except Exception as e:
        print(f"Error saving report to {report_path}: {e}")
        _log_check(report, "report_save", str(report_path), "FAIL", f"Failed to save JSON report. Error: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Katana Doctor - Diagnose and fix environment issues.")
    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Automatically attempt to fix detected issues (e.g., install missing libraries).'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        dest='clear_cache_flag', # Use a different dest to avoid conflict with module name
        help='Clear the HuggingFace cache directory (requires confirmation).'
    )
    args = parser.parse_args()
    run_doctor(args.auto_fix, args.clear_cache_flag)
