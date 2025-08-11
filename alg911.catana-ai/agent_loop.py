import json
import time
from core.state_monitor import StateMonitor
from core.goal_prioritizer import GoalPrioritizer
from core.task_executor import TaskExecutor

# --- Agent MCP (Master Control Program) ---

class KatanaAgent:
    """
    The autonomous Katana agent, driven by the OODA loop.
    """
    def __init__(self):
        print("Initializing Katana Autonomous Agent...")
        self.state_monitor = StateMonitor()
        self.goal_prioritizer = GoalPrioritizer()
        self.task_executor = TaskExecutor()
        print("Agent Initialized. Ready to begin OODA loop.")

    def run_single_cycle(self):
        """
        Executes one full OODA loop cycle.
        Observe -> Orient -> Decide -> Act
        """
        print("\n" + "="*20 + " STARTING OODA CYCLE " + "="*20)

        # 1. OBSERVE: Get a snapshot of the current state
        print("\n--- 1. OBSERVE ---")
        state_report = self.state_monitor.check_state()
        print("State Monitor Report:")
        # A bit of pretty printing for the log
        print(json.dumps(state_report, indent=2, default=str))


        # 2. ORIENT: Analyze the state and prioritize goals
        print("\n--- 2. ORIENT ---")
        prioritized_goals = self.goal_prioritizer.prioritize_goals(state_report)
        print("Prioritized Goals:")
        if not prioritized_goals:
            print("No goals identified. System is nominal.")
        else:
            print(json.dumps(prioritized_goals, indent=2, default=str))


        # 3. DECIDE & 4. ACT: Take the top priority goal and execute it
        if not prioritized_goals:
            print("\n--- 3/4. DECIDE & ACT ---")
            print("No action taken.")
        else:
            top_goal = prioritized_goals[0]
            print(f"\n--- 3. DECIDE ---")
            print(f"Top priority goal selected: {top_goal.get('goal')} (Priority: {top_goal.get('priority')})")

            print("\n--- 4. ACT ---")
            self.task_executor.execute_goal(top_goal)

        print("\n" + "="*21 + " OODA CYCLE END " + "="*22 + "\n")


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
