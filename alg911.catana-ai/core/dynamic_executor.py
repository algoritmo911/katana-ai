import os
import yaml
import json
import requests
from typing import List, Dict, Any

# --- Mock n8n API Client ---
# In a real implementation, this would interact with a running n8n instance.
class MockN8nApiClient:
    def __init__(self, n8n_url, api_key):
        self.n8n_url = n8n_url
        self.api_key = api_key
        print(f"MockN8nApiClient initialized for URL: {n8n_url}")

    def execute_workflow(self, workflow_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        print(f"\n--- Mock n8n executing workflow '{workflow_id}' with params ---\n{json.dumps(params, indent=2)}\n--------------------------------------------------------------\n")

        if workflow_id == "n8n-workflow-web-search":
            # Simulate finding some web pages
            return {
                "status": "success",
                "results": [
                    {"url": "https://en.wikipedia.org/wiki/Cryptography", "title": "Cryptography - Wikipedia"},
                    {"url": "https://www.khanacademy.org/computing/computer-science/cryptography", "title": "Cryptography | Computer science | Khan Academy"}
                ]
            }
        else:
            return {"status": "error", "message": "Workflow not found"}

# --- Dynamic Executor ---

class DynamicExecutor:
    """
    Executes a plan by calling internal functions or triggering external workflows.
    """
    def __init__(self, n8n_url: str, n8n_api_key: str):
        """
        Initializes the DynamicExecutor.
        """
        self.n8n_client = MockN8nApiClient(n8n_url, n8n_api_key)
        self.context = {} # Stores the output of each step
        self._register_internal_actions()

    def _register_internal_actions(self):
        """Maps action names to internal methods."""
        self.action_mapper = {
            "query_memory_weaver": self._query_memory_weaver,
            "generate_search_queries": self._generate_search_queries,
            "execute_web_search": self._execute_web_search,
            "process_and_index_results": self._process_and_index_results,
            "notify_administrator": self._notify_administrator,
        }

    def execute_plan(self, plan: List[Dict[str, Any]]):
        """
        Iterates through a plan and executes each step.
        """
        print("\n" + "="*20 + " EXECUTING PLAN " + "="*20)
        self.context = {} # Reset context for each new plan

        for step in plan:
            step_num = step.get('step')
            action = step.get('action')
            params = step.get('params', {})

            print(f"\n--- Step {step_num}: {action} ---")

            # Resolve parameters using context from previous steps
            try:
                resolved_params = self._resolve_params(params)
            except Exception as e:
                print(f"ERROR: Could not resolve params for step {step_num}. Stopping execution. Error: {e}")
                break

            # Find and execute the action
            action_function = self.action_mapper.get(action)
            if action_function:
                try:
                    result = action_function(resolved_params)
                    # Store the result in the context
                    self.context[f"step_{step_num}"] = {"output": result}
                    print(f"Step {step_num} successful. Output stored in context.")
                except Exception as e:
                    print(f"ERROR: Action '{action}' failed for step {step_num}. Stopping execution. Error: {e}")
                    break
            else:
                print(f"ERROR: Unknown action '{action}' in step {step_num}. Stopping execution.")
                break

        print("\n" + "="*21 + " PLAN EXECUTION FINISHED " + "="*21 + "\n")

    def _resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolves placeholders like '{{steps.1.output.nodes}}' with actual data from the context.
        """
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                path = value.strip(" {}").split('.')
                # e.g., path = ['steps', '1', 'output', 'nodes']
                # Basic resolver for now. A robust implementation would handle nested lookups.
                if len(path) == 4 and path[0] == 'steps' and path[2] == 'output':
                    step_key = f"step_{path[1]}"
                    data_key = path[3]
                    resolved[key] = self.context[step_key]['output'][data_key]
                else:
                    raise ValueError(f"Unsupported placeholder format: {value}")
            else:
                resolved[key] = value
        return resolved

    # --- Internal Action Implementations (Mocks) ---

    def _query_memory_weaver(self, params: Dict) -> Dict:
        print(f"Querying MemoryWeaver with: {params}")
        # Simulate finding related nodes
        return {"nodes": ["AES", "RSA", "public-key cryptography"]}

    def _generate_search_queries(self, params: Dict) -> Dict:
        print(f"Generating search queries with: {params}")
        # Simulate generating queries from related nodes
        return {"search_queries": ["advanced encryption standard", "RSA algorithm explained", "history of public-key cryptography"]}

    def _execute_web_search(self, params: Dict) -> Dict:
        print(f"Executing n8n web search with: {params}")
        workflow_id = params.get("workflow_id")
        return self.n8n_client.execute_workflow(workflow_id, params)

    def _process_and_index_results(self, params: Dict) -> Dict:
        print(f"Processing and indexing results: {params}")
        # Simulate successful indexing
        return {"indexed_count": len(params.get("search_results", [])), "status": "success"}

    def _notify_administrator(self, params: Dict) -> Dict:
        print(f"Sending notification to admin: {params}")
        return {"status": "success", "message_sent": True}

if __name__ == '__main__':
    # This allows for direct testing of the DynamicExecutor
    print("Running DynamicExecutor direct test...")

    # Mock plan for testing
    mock_plan = [
        {'step': 1, 'action': 'query_memory_weaver', 'params': {'topic': 'cryptography', 'query': 'related_nodes'}, 'reason': '...'},
        {'step': 2, 'action': 'generate_search_queries', 'params': {'topic': 'cryptography', 'related_nodes': '{{steps.1.output.nodes}}'}, 'reason': '...'},
        {'step': 3, 'action': 'execute_web_search', 'params': {'queries': '{{steps.2.output.search_queries}}', 'workflow_id': 'n8n-workflow-web-search'}, 'reason': '...'},
        {'step': 4, 'action': 'process_and_index_results', 'params': {'search_results': '{{steps.3.output.results}}', 'topic': 'cryptography'}, 'reason': '...'}
    ]

    executor = DynamicExecutor(n8n_url="http://localhost:5678", n8n_api_key="mock-n8n-api-key")
    executor.execute_plan(mock_plan)
