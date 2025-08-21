import json
import time
from core.state_monitor import StateMonitor
from core.goal_prioritizer import GoalPrioritizer
from core.planner import Planner
from core.task_executor import TaskExecutor

# --- Agent MCP (Master Control Program) ---

class KatanaAgent:
    """
    The autonomous Katana agent, driven by the OODA-P loop.
    Observe -> Orient -> Decide -> Plan -> Act
    """
    def __init__(self):
        print("Initializing Katana Autonomous Agent...")
        self.state_monitor = StateMonitor()
        self.goal_prioritizer = GoalPrioritizer()
        self.planner = Planner()
        self.task_executor = TaskExecutor()
        print("Agent Initialized. Ready to begin OODA-P loop.")

    def run_single_cycle(self):
        """
        Executes one full OODA-P loop cycle.
        Observe -> Orient -> Decide -> Plan -> Act
        """
        print("\n" + "="*20 + " STARTING OODA-P CYCLE " + "="*19)

        # 1. OBSERVE: Get a snapshot of the current state
        print("\n--- 1. OBSERVE ---")
        state_report = self.state_monitor.check_state()
        print("State Monitor Report:")
        print(json.dumps(state_report, indent=2, default=str))

        # 2. ORIENT: Analyze the state and prioritize goals
        print("\n--- 2. ORIENT ---")
        prioritized_goals = self.goal_prioritizer.prioritize_goals(state_report)

        if not prioritized_goals:
            print("No goals identified. System is nominal.")
            print("\n" + "="*21 + " OODA-P CYCLE END " + "="*21 + "\n")
            return

        print("Prioritized Goals:")
        print(json.dumps(prioritized_goals, indent=2, default=str))

        # 3. DECIDE: Select the top priority goal
        top_goal = prioritized_goals[0]
        print(f"\n--- 3. DECIDE ---")
        print(f"Top priority goal selected: {top_goal.get('goal')} (Priority: {top_goal.get('priority')})")

        # 4. PLAN: Generate a sequence of commands to achieve the goal
        print("\n--- 4. PLAN ---")
        plan = self.planner.create_plan(top_goal)

        if not plan:
            print("Planner could not create a plan for the selected goal. Aborting.")
            print("\n" + "="*21 + " OODA-P CYCLE END " + "="*21 + "\n")
            return

        print("Plan Generated:")
        # Pydantic models have a nice `model_dump_json` method
        print(plan.model_dump_json(indent=2))

        # 5. ACT: Execute the generated plan
        print("\n--- 5. ACT ---")
        self.task_executor.execute_plan(plan)

        print("\n" + "="*21 + " OODA-P CYCLE END " + "="*21 + "\n")


def main():
    """
    Main function to run the agent.
    """
    agent = KatanaAgent()

    # For this mission, we run a single cycle.
    # In a real deployment, this would be in a loop with a sleep timer,
    # or triggered by a cron job or external event.
    # e.g., while True:
    #           agent.run_single_cycle()
    #           time.sleep(300) # Wait 5 minutes

    agent.run_single_cycle()


if __name__ == "__main__":
    main()
