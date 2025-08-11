import json
from typing import Dict, Any

class N8nBlueprintGenerator:
    """
    Generates n8n workflow JSON blueprints from predefined templates.
    """

    def generate_workflow(self, template_name: str) -> Dict[str, Any]:
        """
        Generates a workflow based on the provided template name.

        Args:
            template_name: The name of the template to generate.

        Returns:
            A dictionary representing the n8n workflow JSON.

        Raises:
            ValueError: If the template name is not found.
        """
        if template_name == "StandardLeadFunnel":
            return self._build_standard_lead_funnel()
        else:
            raise ValueError(f"Template '{template_name}' not found.")

    def _build_standard_lead_funnel(self) -> Dict[str, Any]:
        """
        Builds the JSON for a standard lead funnel workflow.
        Webhook -> Set -> IF -> Google Sheets / Telegram -> Respond to Webhook.
        """
        return {
            "name": "Standard Lead Funnel",
            "nodes": [
                {
                    "parameters": {
                        "path": "webhook/lead-capture",
                        "options": {}
                    },
                    "name": "Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "position": [240, 300],
                    "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                    "credentials": {}
                },
                {
                    "parameters": {
                        "values": {
                            "string": [
                                {
                                    "name": "leadSource",
                                    "value": "={{$node[\"Webhook\"].json[\"body\"][\"source\"] || 'unknown'}}"
                                }
                            ]
                        },
                        "options": {}
                    },
                    "name": "Set Lead Source",
                    "type": "n8n-nodes-base.set",
                    "typeVersion": 1,
                    "position": [460, 300],
                    "id": "b2c3d4e5-f6a7-8901-2345-67890abcdef1"
                },
                {
                    "parameters": {
                        "conditions": {
                            "string": [
                                {
                                    "value1": "={{$node[\"Set Lead Source\"].json[\"leadSource\"]}}",
                                    "operation": "equal",
                                    "value2": "paid_ads"
                                }
                            ]
                        }
                    },
                    "name": "Is Paid Lead?",
                    "type": "n8n-nodes-base.if",
                    "typeVersion": 1,
                    "position": [680, 300],
                    "id": "c3d4e5f6-a7b8-9012-3456-7890abcdef12"
                },
                {
                    "parameters": {
                        "operation": "append",
                        "documentId": "", # User would fill this in
                        "sheetName": "gid=0", # User would fill this in
                        "fields": {
                            "values": [
                                {
                                    "field": "Timestamp",
                                    "value": "={{$now}}"
                                },
                                {
                                    "field": "LeadData",
                                    "value": "={{JSON.stringify($node[\"Webhook\"].json[\"body\"])}}"
                                }
                            ]
                        }
                    },
                    "name": "Save to Google Sheet",
                    "type": "n8n-nodes-base.googleSheets",
                    "typeVersion": 1,
                    "position": [900, 200],
                    "id": "d4e5f6a7-b8c9-0123-4567-890abcdef123",
                    "credentials": {
                        "googleApi": { # User would configure this
                            "id": "CREDENTIAL_ID_PLACEHOLDER",
                            "name": "My Google API"
                        }
                    }
                },
                {
                    "parameters": {
                        "chatId": "", # User would fill this in
                        "text": "=Lead from non-paid source: {{$node[\"Set Lead Source\"].json[\"leadSource\"]}}",
                        "options": {}
                    },
                    "name": "Notify via Telegram",
                    "type": "n8n-nodes-base.telegram",
                    "typeVersion": 1,
                    "position": [900, 400],
                    "id": "e5f6a7b8-c9d0-1234-5678-90abcdef1234",
                    "credentials": {
                        "telegramApi": { # User would configure this
                            "id": "CREDENTIAL_ID_PLACEHOLDER",
                            "name": "My Telegram API"
                        }
                    }
                },
                {
                    "parameters": {
                        "responseCode": "200",
                        "options": {
                            "responseData": "={{$json.success === false ? { 'status': 'notification_sent' } : { 'status': 'lead_saved' }}}"
                        }
                    },
                    "name": "Respond to Webhook",
                    "type": "n8n-nodes-base.respondToWebhook",
                    "typeVersion": 1,
                    "position": [1120, 300],
                    "id": "f6a7b8c9-d0e1-2345-6789-0abcdef12345"
                }
            ],
            "connections": {
                "Webhook": {
                    "main": [
                        [
                            {
                                "node": "Set Lead Source",
                                "type": "main",
                                "index": 0
                            }
                        ]
                    ]
                },
                "Set Lead Source": {
                    "main": [
                        [
                            {
                                "node": "Is Paid Lead?",
                                "type": "main",
                                "index": 0
                            }
                        ]
                    ]
                },
                "Is Paid Lead?": {
                    "main": [
                        [
                            {
                                "node": "Save to Google Sheet",
                                "type": "main",
                                "index": 0
                            }
                        ],
                        [
                            {
                                "node": "Notify via Telegram",
                                "type": "main",
                                "index": 1
                            }
                        ]
                    ]
                },
                "Save to Google Sheet": {
                    "main": [
                        [
                            {
                                "node": "Respond to Webhook",
                                "type": "main",
                                "index": 0
                            }
                        ]
                    ]
                },
                "Notify via Telegram": {
                    "main": [
                        [
                            {
                                "node": "Respond to Webhook",
                                "type": "main",
                                "index": 0
                            }
                        ]
                    ]
                }
            },
            "active": False,
            "settings": {},
            "id": "workflow_template_1"
        }

    def to_json(self, workflow: Dict[str, Any], pretty: bool = True) -> str:
        """
        Converts a workflow dictionary to a JSON string.

        Args:
            workflow: The workflow dictionary.
            pretty: Whether to format the JSON with indentation.

        Returns:
            A JSON string representation of the workflow.
        """
        if pretty:
            return json.dumps(workflow, indent=2)
        return json.dumps(workflow)
