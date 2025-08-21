import os
import json
import time

from state_monitor import StateMonitor
from goal_synthesizer import GoalSynthesizer
from planner import Planner
from dynamic_executor import DynamicExecutor

# --- DAO Core Configuration ---
CONSTITUTION_PATH = os.path.join(os.path.dirname(__file__), 'constitution.yaml')
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "mock-n8n-api-key")

class DaoCore:
    """
    The Decentralized Autonomous Organization Core for Katana.
    This orchestrates the entire autonomous decision-making loop.
    """
    def __init__(self):
        print("Initializing Katana DAO-Core...")
        self.state_monitor = StateMonitor()
        self.goal_synthesizer = GoalSynthesizer(constitution_path=CONSTITUTION_PATH)
        self.planner = Planner()
        self.dynamic_executor = DynamicExecutor(n8n_url=N8N_URL, n8n_api_key=N8N_API_KEY)
        print("DAO-Core Initialized. Ready to begin autonomous cycle.")

    def run_single_cycle(self):
        """
        Executes one full autonomous cycle:
        Observe -> Synthesize Goal -> Plan -> Execute
        """
        print("\n" + "="*20 + " STARTING DAO CYCLE " + "="*20)

        # 1. OBSERVE: Get a snapshot of the current state
        print("\n--- 1. OBSERVE ---")
        state_report = self.state_monitor.check_state()
        print("State Monitor Report:")
        print(json.dumps(state_report, indent=2, default=str))

        # 2. SYNTHESIZE GOAL: Formulate a high-level goal
        print("\n--- 2. SYNTHESIZE GOAL ---")
        goal = self.goal_synthesizer.synthesize_goal(state_report)
        print("Synthesized Goal:")
        if not goal:
            print("No goal was synthesized. System is nominal or in a safe state.")
        else:
            print(json.dumps(goal, indent=2, default=str))

        # 3. PLAN: Decompose the goal into a sequence of steps
        if not goal or goal.get('priority', 0) < self.goal_synthesizer.constitution.get('goal_synthesis', {}).get('min_priority', 0.5):
            print("\n--- 3/4. PLAN & EXECUTE ---")
            print("Goal does not meet minimum priority or no goal was synthesized. No action will be taken.")
        else:
            print("\n--- 3. PLAN ---")
            plan = self.planner.create_plan(goal)
            print("Generated Plan:")
            if not plan:
                print("No plan could be generated for the goal.")
            else:
                # Using yaml dump for better readability of the plan
                import yaml
                print(yaml.dump(plan, default_flow_style=False, indent=2))

            # 4. EXECUTE: Carry out the plan
            if not plan:
                print("\n--- 4. EXECUTE ---")
                print("No plan to execute.")
            else:
                print("\n--- 4. EXECUTE ---")
                self.dynamic_executor.execute_plan(plan)

        print("\n" + "="*21 + " DAO CYCLE END " + "="*22 + "\n")


def main():
    """
    Main function to run the DAO-Core.
    """
    dao_core = DaoCore()

    # In a real deployment, this would be in a loop with a sleep timer.
    # For this demonstration, we run a single cycle.
    dao_core.run_single_cycle()

if __name__ == "__main__":
    main()
