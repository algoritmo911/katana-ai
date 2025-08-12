import json
from typing import Dict, Any

class N8nScreenshotAnalyzer:
    """
    Analyzes n8n workflow screenshots to reconstruct their logical structure
    and identify potential errors.
    """

    def __init__(self, llm_client: Any):
        """
        Initializes the analyzer with a multimodal LLM client.

        Args:
            llm_client: An instance of a client capable of handling multimodal (text and image) prompts.
        """
        self.llm_client = llm_client

    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """
        Analyzes a screenshot of an n8n workflow.

        Args:
            image_path: The file path to the screenshot image.

        Returns:
            A dictionary representing the JSON structure of the workflow.
        """
        # This is a placeholder for the actual multimodal LLM call.
        # It would involve sending the image and a prompt to the LLM.
        print(f"Analyzing screenshot: {image_path}")

        # The prompt for the LLM
        prompt = (
            "You are a leading expert in n8n. Analyze this screenshot of a workflow. "
            "Identify each node, its type (e.g., Trigger, OpenAI, Telegram), and any visible parameters. "
            "Describe the connections between the nodes. "
            "Return the result as a JSON object with two keys: 'nodes' and 'connections'."
        )

        # In a real implementation, you would use the llm_client to send the image and prompt
        # and get back the JSON response.
        # response = self.llm_client.analyze_image(image_path, prompt)
        # For now, we'll return a mock response.

        # A more realistic mock response for testing the error detection
        mock_response = {
            "nodes": [
                {
                    "id": "1",
                    "name": "Start",
                    "type": "n8n-nodes-base.start"
                },
                {
                    "id": "2",
                    "name": "Get All Users",
                    "type": "n8n-nodes-base.http-request" # Example type
                },
                {
                    "id": "3",
                    "name": "Send Telegram Message",
                    "type": "n8n-nodes-base.telegram"
                }
            ],
            "connections": [
                {"source": "1", "target": "2"},
                {"source": "2", "target": "3"}
            ]
        }

        # In a real implementation, you would parse the LLM's response.
        # return json.loads(response)
        return mock_response

    def find_logical_errors(self, workflow: Dict[str, Any]) -> list[str]:
        """
        Analyzes a workflow's JSON structure to find logical errors.
        The primary error this looks for is an array-producing node connected
        directly to a node that expects a single item.

        Args:
            workflow: A dictionary representing the n8n workflow.

        Returns:
            A list of strings, where each string describes a found logical error.
        """
        errors = []
        nodes = workflow.get("nodes", [])
        connections = workflow.get("connections", [])

        if not nodes or not connections:
            return errors

        # Create a mapping from node ID to node object for easy lookup.
        # The LLM might return node names or IDs in the connections. Let's assume IDs for now.
        # And let's assume the node object contains a 'name' and 'type' field.
        node_map = {node["id"]: node for node in nodes}

        # Keywords to identify node types. This is a simple heuristic.
        # The 'name' of the node is what's visible on the screenshot.
        ARRAY_PRODUCERS_KEYWORDS = ["get all", "list", "read range"] # Lowercase
        SINGLE_ITEM_CONSUMERS_KEYWORDS = ["send", "create", "update", "add", "set"]

        # Nodes that can handle arrays, breaking the error condition
        ARRAY_HANDLER_KEYWORDS = ["split in batches", "code", "function"]

        for connection in connections:
            source_id = connection.get("source")
            target_id = connection.get("target")

            source_node = node_map.get(source_id)
            target_node = node_map.get(target_id)

            if not source_node or not target_node:
                continue

            source_name = source_node.get("name", "").lower()
            target_name = target_node.get("name", "").lower()

            # Check if source produces an array
            source_is_array_producer = any(keyword in source_name for keyword in ARRAY_PRODUCERS_KEYWORDS)

            # Check if target consumes a single item
            target_is_single_item_consumer = any(keyword in target_name for keyword in SINGLE_ITEM_CONSUMERS_KEYWORDS)

            # Check if the target is a known array handler
            target_is_array_handler = any(keyword in target_name for keyword in ARRAY_HANDLER_KEYWORDS)

            if source_is_array_producer and target_is_single_item_consumer and not target_is_array_handler:
                error_message = (
                    f"Logical error detected between node '{source_node.get('name', 'Unknown')}' and '{target_node.get('name', 'Unknown')}'.\n"
                    f"The source node '{source_node.get('name', 'Unknown')}' seems to return an array of items, "
                    f"while the target node '{target_node.get('name', 'Unknown')}' likely expects a single item.\n"
                    "Recommendation: Insert a 'Split In Batches' or a 'Code' node between them to process items one by one."
                )
                errors.append(error_message)

        return errors
