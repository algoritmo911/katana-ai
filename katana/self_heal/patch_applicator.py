import subprocess
import requests

def restart_service(service_name):
    """Restarts a systemd service."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
        return True, f"Service {service_name} restarted successfully."
    except subprocess.CalledProcessError as e:
        return False, f"Failed to restart service {service_name}: {e}"

def apply_patch(patch_file):
    """Applies a git patch."""
    try:
        subprocess.run(["git", "apply", patch_file], check=True)
        return True, f"Patch {patch_file} applied successfully."
    except subprocess.CalledProcessError as e:
        return False, f"Failed to apply patch {patch_file}: {e}"

def rollback_changes():
    """Rolls back the latest git commit."""
    try:
        subprocess.run(["git", "revert", "HEAD", "--no-edit"], check=True)
        return True, "Rolled back the latest commit."
    except subprocess.CalledProcessError as e:
        return False, f"Failed to roll back changes: {e}"

def fetch_patch(patch_url):
    """Fetches a patch from a URL."""
    try:
        response = requests.get(patch_url)
        response.raise_for_status()
        return response.text, "Patch fetched successfully."
    except requests.exceptions.RequestException as e:
        return None, f"Failed to fetch patch: {e}"
