import yaml
from typing import Dict, Any, Optional

class ReflexMap:
    """
    Loads and provides access to the reflex map configuration.
    """

    def __init__(self, file_path: str = "katana/reflex_map.yml"):
        self.file_path = file_path
        self._reflex_map = self._load_map()

    def _load_map(self) -> Dict[str, Any]:
        """Loads the reflex map from the YAML file."""
        try:
            with open(self.file_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Handle case where file doesn't exist
            print(f"Error: Reflex map file not found at {self.file_path}")
            return {"anomalies": []}
        except yaml.YAMLError as e:
            # Handle case where YAML is invalid
            print(f"Error parsing YAML from {self.file_path}: {e}")
            return {"anomalies": []}

    def get_workflow_for_anomaly(self, anomaly_name: str) -> Optional[Dict[str, Any]]:
        """
        Finds the corresponding workflow for a given anomaly name.

        Args:
            anomaly_name: The name of the anomaly to look up.

        Returns:
            A dictionary containing the workflow and its parameters, or None if not found.
        """
        for anomaly in self._reflex_map.get("anomalies", []):
            if anomaly.get("name") == anomaly_name:
                return {
                    "workflow": anomaly.get("workflow"),
                    "params": anomaly.get("params", {}),
                }
        return None

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoHealer:
    """
    Handles anomalies by triggering corrective workflows based on a reflex map.
    """

    def __init__(self, reflex_map: "ReflexMap"):
        """
        Initializes the AutoHealer with a reflex map.

        Args:
            reflex_map: An instance of the ReflexMap class.
        """
        self.reflex_map = reflex_map

    def handle_anomaly(self, anomaly_data: Dict[str, Any]):
        """
        Handles a single anomaly event.

        Args:
            anomaly_data: A dictionary representing the anomaly.
                          Expected to have a 'name' key.
        """
        anomaly_name = anomaly_data.get("name")
        if not anomaly_name:
            logger.warning("Received anomaly with no name. Ignoring.")
            return

        logger.info(f"Handling anomaly: {anomaly_name}")

        workflow_info = self.reflex_map.get_workflow_for_anomaly(anomaly_name)

        if not workflow_info or not workflow_info.get("workflow"):
            logger.warning(f"No workflow found for anomaly: {anomaly_name}. No action taken.")
            return

        self._execute_workflow(workflow_info, anomaly_data)

    def _execute_workflow(self, workflow_info: Dict[str, Any], anomaly_data: Dict[str, Any]):
        """
        Executes the corrective workflow.

        In a real implementation, this would trigger an n8n workflow via an HTTP request.
        For now, it logs the action that would be taken.

        Args:
            workflow_info: The workflow details from the reflex map.
            anomaly_data: The original anomaly data.
        """
        workflow_name = workflow_info["workflow"]
        params = workflow_info["params"]

        # Log the action with high priority
        # This log message is structured to be easily machine-parsable if needed
        logger.critical({
            "event": "auto_healer_action",
            "status": "triggered",
            "anomaly_name": anomaly_data.get("name"),
            "anomaly_details": anomaly_data.get("details", {}),
            "corrective_action": {
                "workflow_name": workflow_name,
                "parameters": params,
            },
        })

        print(f"Executing workflow '{workflow_name}' with params: {params}")
        # In the future, this is where we would add the HTTP client call to n8n:
        #
        # import requests
        # try:
        #     # The n8n webhook URL would likely be constructed from the workflow_name
        #     # or retrieved from a config.
        #     webhook_url = f"https://n8n.example.com/webhook/{workflow_name}"
        #     response = requests.post(webhook_url, json={"anomaly": anomaly_data, "params": params})
        #     response.raise_for_status()
        #     logger.info(f"Successfully triggered workflow {workflow_name}. Status: {response.status_code}")
        # except requests.RequestException as e:
        #     logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
