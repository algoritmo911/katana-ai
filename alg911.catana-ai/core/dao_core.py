import os
import json
import time
import yaml

# Components for the outer loop
from state_monitor import StateMonitor
from planner import Planner
from dynamic_executor import DynamicExecutor

# The new cognitive layer: The Parliament of Minds
from core.personas.analyst import Analyst
from core.personas.strategist import Strategist
from core.personas.ethicist import Ethicist
from core.personas.apophatic import Apophatic


# --- DAO Core Configuration ---
CONSTITUTION_PATH = os.path.join(os.path.dirname(__file__), 'constitution.yaml')
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "mock-n8n-api-key")


class ParliamentOfMinds:
    """
    Orchestrates the "Parliament of Minds" cognitive architecture.
    This replaces the simple GoalSynthesizer with a structured debate
    between multiple AI personas to arrive at a synthesized goal.
    """
    def __init__(self):
        print("Initializing the Parliament of Minds...")

        # The different aspects of the agent's "mind"
        self.analyst = Analyst()
        self.strategist = Strategist()
        self.ethicist = Ethicist(constitution_path=CONSTITUTION_PATH)
        self.apophatic = Apophatic()

        # The existing execution modules
        self.planner = Planner()
        self.dynamic_executor = DynamicExecutor(n8n_url=N8N_URL, n8n_api_key=N8N_API_KEY)
        # The state monitor is still needed to provide context, though not for the trigger.
        self.state_monitor = StateMonitor()

        print("Parliament initialized. Ready to convene.")

    def run_debate_cycle(self, trigger_data: dict):
        """
        Executes one full cognitive debate cycle based on a trigger.
        This is the core of Protocol "Athena".
        """
        print("\n" + "="*20 + " CONVENING THE PARLIAMENT " + "="*20)
        print(f"Triggering issue: {trigger_data.get('summary', 'N/A')}")

        # --- DEBATE PROTOCOL ---

        # Step 1: Analyst formulates the problem and proposes goals
        print("\n--- [Step 1] Analyst: Problem Formulation ---")
        # For the mock, we need to pass a string representation of the dict
        analyst_report = self.analyst.analyze_dissonance(str(trigger_data))
        # Mock parsing of the analyst's report to extract goals
        # In a real system, this would parse a structured format like JSON or YAML
        proposed_goals = [line.strip() for line in analyst_report.split('\n') if "Goal" in line or "issue" in line]
        print(f"Analyst proposed goals: {proposed_goals}")


        # Step 2: Strategist evaluates the goals
        print("\n--- [Step 2] Strategist: Strategic Evaluation ---")
        strategic_evaluation = self.strategist.evaluate_goals(proposed_goals)
        # Mock parsing: assume the strategist picks the first goal as most effective
        strategic_goal = proposed_goals[0] if proposed_goals else "No goal proposed"
        print(f"Strategist's recommendation: '{strategic_goal}'")


        # Step 3: Ethicist checks for constitutional compliance
        print("\n--- [Step 3] Ethicist: Ethical Veto ---")
        compliance_report = self.ethicist.check_compliance([strategic_goal])
        # Mock parsing: check if the report contains "Violates"
        if "Violates" in compliance_report:
            print(f"Ethical Veto! The goal '{strategic_goal}' violates the constitution. Halting cycle.")
            print("\n" + "="*21 + " PARLIAMENT ADJOURNED " + "="*22 + "\n")
            return
        print("Goal is compliant with the Constitution.")
        compliant_goal = strategic_goal


        # Step 4: Apophatic (Devil's Advocate) tries to find a flaw
        print("\n--- [Step 4] Apophatic: Devil's Advocate ---")
        critique = self.apophatic.find_flaw(compliant_goal)
        if "SILENCE" not in critique:
            print(f"Apophatic found a critical flaw: {critique}")
            print("Cycle halted due to critical flaw. A new debate should be initiated with this critique.")
            print("\n" + "="*21 + " PARLIAMENT ADJOURNED " + "="*22 + "\n")
            return
        print("Apophatic finds no critical flaws.")


        # Step 5: Final Synthesis
        print("\n--- [Step 5] DAO-Core: Final Synthesis ---")
        final_goal_text = compliant_goal
        # We need to structure this as a goal dictionary for the planner
        final_goal = {
            "goal": final_goal_text.split(':')[0].strip(),
            "reason": f"Synthesized through parliamentary debate. Analyst proposal refined by Strategist, approved by Ethicist, and passed Apophatic critique.",
            "priority": 0.9 # High priority as it comes from a full debate
        }
        print("Final Synthesized Goal:")
        print(json.dumps(final_goal, indent=2))


        # --- Execution Phase ---
        print("\n--- Plan ---")
        plan = self.planner.create_plan(final_goal)
        if plan:
            print(yaml.dump(plan, default_flow_style=False, indent=2))
        else:
            print("No plan could be generated.")

        print("\n--- Execute ---")
        if plan:
            self.dynamic_executor.execute_plan(plan)
        else:
            print("No plan to execute.")

        print("\n" + "="*21 + " PARLIAMENT ADJOURNED " + "="*22 + "\n")


def main():
    """
    Main function to run the Parliament of Minds.
    """
    parliament = ParliamentOfMinds()

    # Path to the mock queue, assuming dao_core.py is in the 'core' directory
    queue_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cognitive_dissonance_queue.json')

    print(f"\n--- Monitoring Cognitive Dissonance Queue at {queue_path} ---")

    try:
        with open(queue_path, 'r') as f:
            queue = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing queue file: {e}")
        return

    unresolved_issues = [issue for issue in queue if issue.get('status') == 'unresolved']

    if not unresolved_issues:
        print("No unresolved issues in the queue. System is in harmony.")
        return

    print(f"Found {len(unresolved_issues)} unresolved issue(s). Convening parliament for the first one.")

    # For this test, we process the first unresolved issue
    issue_to_debate = unresolved_issues[0]

    # The trigger data passed to the debate cycle is the 'details' field of the issue
    parliament.run_debate_cycle(issue_to_debate['details'])


if __name__ == "__main__":
    main()
