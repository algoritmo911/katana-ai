import os
import yaml
import datetime

# --- Mock LLM Client ---
# In a real implementation, this would be a client for an actual LLM service
# like OpenAI, Anthropic, etc.
class MockLLMClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def generate(self, prompt, max_tokens=100):
        # This mock function simulates the LLM's goal synthesis process.
        # It will generate a plausible goal based on keywords in the prompt.
        print(f"\n--- Mock LLM generating goal from prompt ---\n{prompt}\n-------------------------------------------\n")
        return "{\"goal\": \"find_and_index_new_sources\", \"topic\": \"cryptography\", \"reason\": \"Detected low knowledge connectivity in the graph for 'cryptography' while system fatigue is low.\", \"priority\": 0.8}"

# --- Goal Synthesizer ---

class GoalSynthesizer:
    """
    Synthesizes a goal based on the agent's constitution and current state.
    """
    def __init__(self, constitution_path, llm_api_key="mock_api_key"):
        """
        Initializes the GoalSynthesizer.
        :param constitution_path: Path to the constitution.yaml file.
        :param llm_api_key: API key for the LLM service.
        """
        self.constitution = self._load_constitution(constitution_path)
        self.llm_client = MockLLMClient(api_key=llm_api_key)

    def _load_constitution(self, path):
        """Loads the constitution from a YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"CRITICAL: Could not load constitution file from {path}: {e}")
            # Return a default, safe constitution if loading fails
            return {
                'goal': 'maintain_system_health',
                'constraints': {'system_fatigue': '< 1.0'},
                'goal_synthesis': {'min_priority': 0.1, 'max_goals': 1}
            }

    def _evaluate_constraints(self, state_report):
        """
        Check if the current state violates any constraints.
        This is a simplified implementation. A real one would parse the constraint strings.
        """
        # Mock implementation of system fatigue check
        system_fatigue = state_report.get('performance_issues', [])
        if system_fatigue: # Simple check: any performance issue means high fatigue
             return False, "System fatigue is high."
        return True, "System fatigue is low."


    def synthesize_goal(self, state_report):
        """
        Formulates a goal using the constitution and state report.
        """
        constraints_ok, reason = self._evaluate_constraints(state_report)

        # Build a detailed prompt for the LLM
        prompt = f"""
        **Constitution:**
        - High-level goal: {self.constitution.get('goal')}
        - Constraints: {self.constitution.get('constraints')}

        **Current State Report:**
        - Timestamp: {state_report.get('report_timestamp')}
        - Unresolved Tasks: {len(state_report.get('unresolved_tasks', []))}
        - Critical Errors: {len(state_report.get('critical_errors', []))}
        - Performance Issues: {len(state_report.get('performance_issues', []))}
        - Constraint Check: {reason}

        **Analysis:**
        - Based on the constitution and the current state, what is the most important, achievable goal right now?
        - The goal should be a single, actionable item.
        - Consider the high-level goal of '{self.constitution.get('goal')}' and the immediate needs from the state report.
        - If there are critical errors, they should be the top priority.
        - If constraints are violated, the goal should be to reduce the load.
        - If the system is healthy and there are no urgent tasks, propose a goal that aligns with the primary directive. For example, if knowledge connectivity is low in a certain area, suggest a goal to improve it.
        - For this simulation, assume a low knowledge connectivity for the topic 'cryptography'.

        **Output Format:**
        Return a single JSON object with the following keys: 'goal', 'reason', 'priority', and optional 'details' or 'topic'.
        Example: {{"goal": "find_and_index_new_sources", "topic": "cryptography", "reason": "...", "priority": 0.8}}
        """

        # Use the LLM to generate a goal
        generated_goal_json = self.llm_client.generate(prompt)

        try:
            goal = yaml.safe_load(generated_goal_json)
            return goal
        except yaml.YAMLError as e:
            print(f"ERROR: Could not parse LLM response as JSON: {e}")
            return None


if __name__ == '__main__':
    # This allows for direct testing of the GoalSynthesizer
    print("Running GoalSynthesizer direct test...")

    # Assume the constitution is in the same directory for testing
    current_dir = os.path.dirname(os.path.abspath(__file__))
    constitution_file = os.path.join(current_dir, 'constitution.yaml')

    # Create a dummy constitution file if it doesn't exist
    if not os.path.exists(constitution_file):
        with open(constitution_file, 'w') as f:
            yaml.dump({
                'goal': 'maximize_knowledge_connectivity',
                'constraints': {'system_fatigue': '< 0.9'}
            }, f)

    synthesizer = GoalSynthesizer(constitution_path=constitution_file)

    # --- Test Case 1: System is healthy, pursue primary goal ---
    print("\n--- Test Case 1: System is Healthy ---")
    mock_state_healthy = {
        'unresolved_tasks': [],
        'critical_errors': [],
        'performance_issues': [],
        'report_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    goal1 = synthesizer.synthesize_goal(mock_state_healthy)
    print("Synthesized Goal:", goal1)


    # --- Test Case 2: Critical error detected ---
    print("\n--- Test Case 2: Critical Error Detected ---")
    mock_state_error = {
        'unresolved_tasks': [],
        'critical_errors': ['CRITICAL: Database connection lost'],
        'performance_issues': [],
        'report_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    goal2 = synthesizer.synthesize_goal(mock_state_error)
    print("Synthesized Goal:", goal2)
