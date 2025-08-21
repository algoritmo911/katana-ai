import os
import json
from tools.n8n_client import N8nClient

# --- User Provided Credentials ---
N8N_URL = "https://korvin.app.n8n.cloud"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxYWIxYTZlOC0zNTliLTRhNjctOWRlNy0xZDY1MzgzMTdlYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUxMTk2NjcxLCJleHAiOjE3NTg5Mjc2MDB9.cQdb8UCFAYAfJGBolIXzZW9ROMxKEznRbBZV2BjtuT8"
WORKFLOW_ID = "sgMlcZDEcZWlHP6X"

def main():
    """Main function to run the workflow diagnosis."""
    print("--- Starting RAW Workflow Diagnosis ---")
    client = N8nClient(n8n_url=N8N_URL, api_key=N8N_API_KEY)

    try:
        # Get the current workflow
        print(f"Fetching workflow '{WORKFLOW_ID}' to diagnose...")
        workflow = client.get_workflow(WORKFLOW_ID)
        print("--- Diagnosis Complete ---")
        print("Raw JSON response from server:")
        print(json.dumps(workflow, indent=2))

    except Exception as e:
        print(f"\n--- CRITICAL FAILURE DURING DIAGNOSIS ---")
        print(f"  - Error: {e}")

if __name__ == '__main__':
    main()
