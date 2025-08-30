import os
import httpx
from typing import Dict, Any

class N8nClient:
    """
    A client for interacting with an n8n instance.
    Specifically, for triggering workflows via webhooks.
    """
    def __init__(self):
        """
        Initializes the n8n client.
        Reads the workflow trigger URL from environment variables.
        """
        self.trigger_url = os.getenv("N8N_WORKFLOW_TRIGGER_URL")
        if not self.trigger_url:
            print("Warning: N8N_WORKFLOW_TRIGGER_URL environment variable is not set. n8n client will be disabled.")

    async def trigger_workflow(self, payload: Dict[str, Any]) -> bool:
        """
        Triggers an n8n workflow by sending a POST request to the configured webhook URL.

        Args:
            payload: A dictionary containing the data to send to the workflow.

        Returns:
            True if the workflow was triggered successfully (i.e., received a 2xx response),
            False otherwise.
        """
        if not self.trigger_url:
            print("Error: Cannot trigger n8n workflow because N8N_WORKFLOW_TRIGGER_URL is not set.")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.trigger_url, json=payload, timeout=10.0)
                response.raise_for_status()  # Raises an exception for 4xx or 5xx status codes
                print(f"Successfully triggered n8n workflow with payload: {payload}")
                return True
        except httpx.RequestError as e:
            print(f"Error triggering n8n workflow: An error occurred while requesting {e.request.url!r}.")
            return False
        except httpx.HTTPStatusError as e:
            print(f"Error triggering n8n workflow: Received status code {e.response.status_code} for {e.request.url!r}.")
            return False
        except Exception as e:
            print(f"An unexpected error occurred while triggering n8n workflow: {e}")
            return False
