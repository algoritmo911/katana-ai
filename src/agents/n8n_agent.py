import json

class N8nAgent:
    """
    A specialized agent for creating and managing n8n workflows.
    """

    def create_workflow(self, task_description: str) -> str:
        """
        Generates an n8n workflow JSON based on a task description.

        For this initial version, it returns a hardcoded, complex workflow
        for a typical e-commerce order processing task.

        Args:
            task_description: A description of the desired workflow.
                              (Currently unused, for future development).

        Returns:
            A JSON string representing the n8n workflow.
        """

        # A sample hardcoded n8n workflow for e-commerce order processing.
        # This workflow is triggered by a webhook, processes a payment via Stripe,
        # and sends a confirmation to Telegram.
        workflow = {
            "name": "E-commerce Order Processing",
            "nodes": [
                {
                    "parameters": {
                        "path": "webhook/order-received",
                        "options": {}
                    },
                    "name": "Webhook Trigger",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "position": [250, 300]
                },
                {
                    "parameters": {
                        "authentication": "stripeApi",
                        "resource": "charge",
                        "operation": "create",
                        "amount": "={{$json.body.amount}}",
                        "currency": "usd",
                        "source": "={{$json.body.stripeToken}}",
                        "description": "Charge for order {{$json.body.orderId}}"
                    },
                    "name": "Process Payment",
                    "type": "n8n-nodes-base.stripe",
                    "typeVersion": 1,
                    "position": [450, 300]
                },
                {
                    "parameters": {
                        "chatId": "={{$json.body.telegramChatId}}",
                        "text": "✅ Payment successful for order {{$json.body.orderId}}! Your items are being prepared.",
                        "options": {}
                    },
                    "name": "Send Telegram Confirmation",
                    "type": "n8n-nodes-base.telegram",
                    "typeVersion": 1,
                    "position": [650, 300]
                }
            ],
            "connections": {
                "Webhook Trigger": {
                    "main": [
                        [
                            {
                                "node": "Process Payment",
                                "type": "main"
                            }
                        ]
                    ]
                },
                "Process Payment": {
                    "main": [
                        [
                            {
                                "node": "Send Telegram Confirmation",
                                "type": "main"
                            }
                        ]
                    ]
                }
            },
            "active": True,
            "settings": {},
            "id": "1"
        }

        return json.dumps(workflow, indent=4)

if __name__ == '__main__':
    # Example usage:
    agent = N8nAgent()
    task_desc = "Create a workflow for processing new orders."
    generated_workflow_json = agent.create_workflow(task_desc)
    print("Generated n8n Workflow JSON:")
    print(generated_workflow_json)

    # Verify it's valid JSON
    try:
        loaded_json = json.loads(generated_workflow_json)
        print("\nJSON is valid.")
        print(f"Workflow Name: {loaded_json.get('name')}")
    except json.JSONDecodeError as e:
        print(f"\nError: Generated output is not valid JSON. {e}")
