import os
import httpx
from typing import List, Dict, Any

class N8nApiClient:
    """
    An asynchronous client for interacting with the n8n REST API.
    """

    def __init__(self, n8n_url: str = None, api_key: str = None):
        """
        Initializes the n8n API client.

        Args:
            n8n_url: The URL of the n8n instance. Defaults to env var N8N_URL.
            api_key: The API key for authentication. Defaults to env var N8N_API_KEY.
        """
        self.n8n_url = n8n_url or os.getenv("N8N_URL")
        self.api_key = api_key or os.getenv("N8N_API_KEY")

        if not self.n8n_url:
            raise ValueError("n8n URL must be provided or set as N8N_URL environment variable.")
        if not self.api_key:
            raise ValueError("n8n API key must be provided or set as N8N_API_KEY environment variable.")

        self.base_url = f"{self.n8n_url.rstrip('/')}/api/v1"
        self.headers = {
            "Accept": "application/json",
            "X-N8N-API-KEY": self.api_key,
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        A helper method to make requests to the n8n API.

        Args:
            method: The HTTP method (GET, POST, PUT, DELETE).
            endpoint: The API endpoint to call.
            **kwargs: Additional arguments to pass to the httpx request.

        Returns:
            The JSON response from the API.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            print(f"API Error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"Request Error: Failed to connect to {e.request.url}")
            raise

    async def get_workflows(self) -> List[Dict[str, Any]]:
        """Retrieves a list of all workflows."""
        return await self._request("GET", "workflows")

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Retrieves a single workflow by its ID."""
        return await self._request("GET", f"workflows/{workflow_id}")

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new workflow.
        Note: The initial workflow structure should be imported from a template or file.
        This method is for creating a new workflow resource from a full JSON payload.
        """
        # The API for creation might be POST to /workflows
        return await self._request("POST", "workflows/import", json=workflow_data)

    async def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an existing workflow."""
        return await self._request("PUT", f"workflows/{workflow_id}", json=workflow_data)

    async def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deletes a workflow by its ID."""
        return await self._request("DELETE", f"workflows/{workflow_id}")

    async def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activates a workflow."""
        return await self._request("POST", f"workflows/{workflow_id}/activate")

    async def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Deactivates a workflow."""
        return await self._request("POST", f"workflows/{workflow_id}/deactivate")

    async def get_executions(self, workflow_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Gets the execution history for a workflow."""
        return await self._request("GET", f"executions?workflowId={workflow_id}&limit={limit}")

    async def get_execution_data(self, execution_id: str) -> Dict[str, Any]:
        """Gets detailed data for a single execution."""
        return await self._request("GET", f"executions/{execution_id}")
