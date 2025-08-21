import requests
import os
import json

class N8nClient:
    """
    A client for interacting with the n8n REST API.
    """

    def __init__(self, n8n_url: str, api_key: str):
        """
        Initializes the n8n client.

        Args:
            n8n_url: The base URL of the n8n instance (e.g., http://localhost:5678).
            api_key: The API key for authentication.
        """
        if not n8n_url:
            raise ValueError("n8n URL cannot be empty.")
        if not api_key:
            raise ValueError("API key cannot be empty.")

        self.base_url = f"{n8n_url.rstrip('/')}/api/v1"
        self.api_key = api_key

    @property
    def _headers(self) -> dict:
        """
        Returns the headers required for API requests.
        """
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-N8N-API-KEY': self.api_key
        }

    def get_workflow(self, workflow_id: str) -> dict:
        """
        Retrieves a specific workflow by its ID.

        Args:
            workflow_id: The ID of the workflow to retrieve.

        Returns:
            A dictionary representing the workflow.
        """
        url = f"{self.base_url}/workflows/{workflow_id}"
        try:
            response = requests.get(url, headers=self._headers)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while getting workflow {workflow_id}: {e}")
            raise

    def update_workflow(self, workflow_id: str, workflow_data: dict) -> dict:
        """
        Updates a specific workflow.

        Args:
            workflow_id: The ID of the workflow to update.
            workflow_data: The full workflow object as a dictionary.

        Returns:
            The response from the server as a dictionary.
        """
        url = f"{self.base_url}/workflows/{workflow_id}"
        try:
            response = requests.put(url, headers=self._headers, data=json.dumps(workflow_data))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while updating workflow {workflow_id}: {e}")
            raise

if __name__ == '__main__':
    # Example usage, requires environment variables N8N_URL and N8N_API_KEY
    # This part is for testing the client directly.
    n8n_url = os.getenv("N8N_URL")
    n8n_api_key = os.getenv("N8N_API_KEY")
    # You would also need a valid workflow ID to test
    workflow_id_to_test = os.getenv("N8N_TEST_WORKFLOW_ID")

    if not all([n8n_url, n8n_api_key, workflow_id_to_test]):
        print("Please set N8N_URL, N8N_API_KEY, and N8N_TEST_WORKFLOW_ID environment variables to run this example.")
    else:
        client = N8nClient(n8n_url=n8n_url, api_key=n8n_api_key)

        # 1. Get the workflow
        print(f"Fetching workflow: {workflow_id_to_test}")
        try:
            workflow = client.get_workflow(workflow_id_to_test)
            print("Successfully fetched workflow.")
            # print(json.dumps(workflow, indent=2))

            # 2. Example modification (e.g., add a note to the workflow)
            # In a real scenario, you would modify the nodes or connections here.
            # For this example, we just add a dummy note to the first node.
            if workflow.get('nodes'):
                workflow['nodes'][0]['notes'] = f"Updated via API at {__import__('datetime').datetime.now()}"
                print("Modified workflow in memory.")

                # 3. Update the workflow
                print(f"Updating workflow: {workflow_id_to_test}")
                update_response = client.update_workflow(workflow_id_to_test, workflow)
                print("Successfully updated workflow.")
                # print(json.dumps(update_response, indent=2))
            else:
                print("Workflow has no nodes to update.")

        except Exception as e:
            print(f"An error occurred during the example run: {e}")
