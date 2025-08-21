import os
import httpx

class N8nBus:
    def __init__(self, webhook_url=None):
        """
        Initializes the n8n bus adapter.
        The webhook URL can be passed directly or sourced from an environment variable.
        """
        self.webhook_url = webhook_url or os.getenv("N8N_WEBHOOK_URL")

        if not self.webhook_url:
            raise ValueError("n8n webhook URL must be provided either as an argument or an environment variable.")

    def send_command(self, command_data):
        """
        Sends a command to the n8n webhook.
        'command_data' is a dictionary representing the command and its parameters.
        """
        try:
            with httpx.Client() as client:
                response = client.post(self.webhook_url, json=command_data)
                response.raise_for_status()  # Raise an exception for bad status codes

            print(f"Successfully sent command to n8n: {command_data}")
            return {"status": "success", "response": response.json()}

        except httpx.RequestError as e:
            print(f"An error occurred while sending command to n8n: {e}")
            return {"status": "error", "message": str(e)}
        except httpx.HTTPStatusError as e:
            print(f"Received an error response from n8n: {e.response.status_code} {e.response.text}")
            return {"status": "error", "message": f"n8n returned status {e.response.status_code}"}
