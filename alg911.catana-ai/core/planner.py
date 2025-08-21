import os
import yaml

# --- Mock LLM Client for Planning ---
class MockLLMClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate(self, prompt, max_tokens=200):
        # This mock function simulates the LLM's planning process.
        print(f"\n--- Mock LLM generating plan from prompt ---\n{prompt}\n------------------------------------------\n")
        if "find_and_index_new_sources" in prompt:
            plan = """
- step: 1
  action: "query_memory_weaver"
  params:
    topic: "cryptography"
    query: "related_nodes"
  reason: "Find existing knowledge to avoid redundancy."
- step: 2
  action: "generate_search_queries"
  params:
    topic: "cryptography"
    related_nodes: "{{steps.1.output.nodes}}"
  reason: "Create effective search terms based on existing knowledge."
- step: 3
  action: "execute_web_search"
  params:
    queries: "{{steps.2.output.search_queries}}"
    workflow_id: "n8n-workflow-web-search"
  reason: "Use the n8n web search workflow to find new external sources."
- step: 4
  action: "process_and_index_results"
  params:
    search_results: "{{steps.3.output.results}}"
    topic: "cryptography"
  reason: "Add the new findings to the knowledge graph via MemoryWeaver."
"""
            return plan
        else:
            plan = """
- step: 1
  action: "notify_administrator"
  params:
    channel: "#system-alerts"
    message: "An unplannable goal was received: {{goal.name}}"
  reason: "Alert admin about an unexpected or unhandled goal."
"""
            return plan

# --- Planner ---

class Planner:
    """
    Decomposes a high-level goal into a sequence of executable steps.
    """
    def __init__(self, llm_api_key="mock_api_key"):
        """
        Initializes the Planner.
        :param llm_api_key: API key for the LLM service.
        """
        self.llm_client = MockLLMClient(api_key=llm_api_key)

    def create_plan(self, goal: dict):
        """
        Generates a step-by-step plan to achieve the given goal.
        """
        if not goal or 'goal' not in goal:
            print("ERROR: Invalid goal provided to Planner.")
            return []

        # Build a detailed prompt for the LLM
        prompt = f"""
        **Goal:** {goal.get('goal')}
        **Topic:** {goal.get('topic')}
        **Reason:** {goal.get('reason')}

        **Task:**
        Decompose this goal into a sequence of concrete, executable steps.
        Each step must be an action that can be mapped to an n8n workflow or an internal agent function.
        Available actions include:
        - query_memory_weaver: Get information from the knowledge graph.
        - generate_search_queries: Use NLP to create search terms.
        - execute_web_search: Trigger an n8n workflow to search the web.
        - process_and_index_results: Add new information to the knowledge graph.
        - notify_administrator: Send an alert to an admin.

        **Output Format:**
        Return a YAML formatted list of steps. Each step should be a dictionary with 'step', 'action', 'params', and 'reason'.
        Use placeholders like `{{{{steps.1.output.nodes}}}}` to indicate data flow between steps.

        Example:
        ```yaml
        - step: 1
          action: "action_name"
          params: {{key: "value"}}
          reason: "Why this step is necessary."
        ```
        """

        # Use the LLM to generate the plan
        generated_plan_yaml = self.llm_client.generate(prompt)

        try:
            plan = yaml.safe_load(generated_plan_yaml)
            return plan
        except yaml.YAMLError as e:
            print(f"ERROR: Could not parse LLM response as YAML: {e}")
            return []


if __name__ == '__main__':
    # This allows for direct testing of the Planner
    print("Running Planner direct test...")
    planner = Planner()

    # --- Test Case 1: Plan for knowledge acquisition ---
    print("\n--- Test Case 1: Knowledge Acquisition Goal ---")
    knowledge_goal = {
        "goal": "find_and_index_new_sources",
        "topic": "cryptography",
        "reason": "Detected low knowledge connectivity.",
        "priority": 0.8
    }
    plan1 = planner.create_plan(knowledge_goal)
    # Pretty print the YAML output
    print("Generated Plan:")
    print(yaml.dump(plan1, default_flow_style=False, indent=2))


    # --- Test Case 2: Unplannable goal ---
    print("\n--- Test Case 2: Unplannable Goal ---")
    unplannable_goal = {
        "goal": "make_coffee",
        "reason": "Agent is thirsty.",
        "priority": 0.9
    }
    plan2 = planner.create_plan(unplannable_goal)
    print("Generated Plan:")
    print(yaml.dump(plan2, default_flow_style=False, indent=2))
