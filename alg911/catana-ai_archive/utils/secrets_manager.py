
# alg911/catana-ai/utils/secrets_manager.py
from google.cloud import secretmanager
import os # For print fallback if logging isn't set up here
from typing import Optional # For type hinting

# It's good practice to define a logger if this module grows,
# but for a single function, print statements to stdout/stderr are okay
# if it's clear they are from this utility.

def get_secret(secret_id: str, project_id: str, version_id: str = "latest") -> Optional[str]:
    """
    Fetches a secret from Google Secret Manager.

    Args:
        secret_id: The ID (name) of the secret.
        project_id: The Google Cloud project ID.
        version_id: The version of the secret (defaults to "latest").

    Returns:
        The secret string if successful, None otherwise.
    """
    try:
        # Ensure GOOGLE_APPLICATION_CREDENTIALS is set in the environment where this runs.
        # For local testing, it might be, for cloud environment, service account usually handles it.
        client = secretmanager.SecretManagerServiceClient()
        secret_version_name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

        print(f"[secrets_manager] Attempting to access secret: {secret_version_name}")
        response = client.access_secret_version(name=secret_version_name)
        payload = response.payload.data.decode("UTF-8")
        print(f"[secrets_manager] Successfully fetched secret '{secret_id}'.")
        return payload
    except Exception as e:
        print(f"[secrets_manager] ERROR: Could not fetch secret '{secret_id}'. Project: '{project_id}'. Error: {e}")
        if "PermissionDenied" in str(e):
            print("[secrets_manager] Hint: Check IAM permissions for the Secret Manager Secret Accessor role on the service account or principal running this code.")
        elif "NotFound" in str(e): # google.api_core.exceptions.NotFound
            print(f"[secrets_manager] Hint: Ensure secret '{secret_id}' (and version '{version_id}') exists in project '{project_id}'.")
        elif "INVALID_ARGUMENT" in str(e): # google.api_core.exceptions.InvalidArgument
             print(f"[secrets_manager] Hint: Secret name or project ID format might be incorrect: {secret_version_name}")
        # import traceback # For very detailed debugging
        # print(traceback.format_exc())
        return None
