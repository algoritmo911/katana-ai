import uuid
from typing import Dict, Any, Optional

# Adjust path to import schemas from the parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import Plan, Command, CommandType

class Planner:
    """
    Generates a concrete plan of execution (a sequence of commands)
    based on a high-level goal.
    """

    def create_plan(self, goal: Dict[str, Any]) -> Optional[Plan]:
        """
        Creates a plan for a given goal.

        This implementation uses a simple rule-based mapping from goal type
        to a predefined plan template.

        :param goal: A dictionary representing the goal from GoalPrioritizer.
        :return: A Plan object or None if no plan can be created.
        """
        goal_type = goal.get('goal')
        if not goal_type:
            return None

        plan_id = f"plan-{uuid.uuid4()}"

        # Using a dispatch table to find the appropriate plan creation method
        plan_creator = getattr(self, f"_create_plan_for_{goal_type}", None)

        if plan_creator:
            return plan_creator(goal, plan_id)

        print(f"Warning: No plan creator found for goal: {goal_type}")
        return None

    def _create_plan_for_answer_user_question(self, goal: Dict[str, Any], plan_id: str) -> Plan:
        """Creates the plan for answering a user's question."""
        details = goal.get('details', {})
        user_id = details.get('user_id')

        return Plan(
            goal="answer_user_question",
            plan_id=plan_id,
            steps=[
                Command(
                    name="memory.retrieve_full_context",
                    type=CommandType.LOCAL_PYTHON,
                    params={"user_id": user_id, "details": details}
                ),
                Command(
                    name="nlp.generate_answer",
                    type=CommandType.LOCAL_PYTHON,
                    # Parameters for this step will be the output of the previous one.
                    # The executor will handle this data flow.
                    params={}
                ),
                Command(
                    name="n8n.webhook",
                    type=CommandType.N8N_WEBHOOK,
                    params={
                        "webhook_url": os.environ.get("N8N_WEBHOOK_SEND_TELEGRAM", "https://n8n.katana.foo/webhook/send-message"),
                        "payload": {
                            "user_id": user_id,
                            # The executor will resolve this special value
                            "text": "context:generated_answer"
                        }
                    }
                )
            ]
        )

    def _create_plan_for_notify_admin_about_crash(self, goal: Dict[str, Any], plan_id: str) -> Plan:
        """Creates the plan for notifying an admin about a system crash."""
        return self._create_generic_admin_notification_plan(
            goal_name="notify_admin_about_crash",
            goal_details=goal.get('details', {}),
            plan_id=plan_id
        )

    def _create_plan_for_notify_admin_about_db_failure(self, goal: Dict[str, Any], plan_id: str) -> Plan:
        """Creates the plan for notifying an admin about a database failure."""
        return self._create_generic_admin_notification_plan(
            goal_name="notify_admin_about_db_failure",
            goal_details=goal.get('details', {}),
            plan_id=plan_id
        )

    def _create_plan_for_investigate_performance_issue(self, goal: Dict[str, Any], plan_id: str) -> Plan:
        """Creates the plan for notifying an admin about a performance issue."""
        return self._create_generic_admin_notification_plan(
            goal_name="investigate_performance_issue",
            goal_details=goal.get('details', {}),
            plan_id=plan_id
        )

    def _create_generic_admin_notification_plan(self, goal_name: str, goal_details: Dict[str, Any], plan_id: str) -> Plan:
        """A generic template for plans that notify administrators."""
        return Plan(
            goal=goal_name,
            plan_id=plan_id,
            steps=[
                Command(
                    name="admin_notifications.format_error_report",
                    type=CommandType.LOCAL_PYTHON,
                    params={"details": goal_details}
                ),
                Command(
                    name="admin_notifications.send_admin_notification",
                    type=CommandType.LOCAL_PYTHON,
                    params={} # Expects output from previous step
                )
            ]
        )


if __name__ == '__main__':
    # Example usage for testing
    planner = Planner()

    # --- Test Case 1: User Question ---
    print(">>> TEST CASE 1: Answer User Question <<<")
    user_question_goal = {
        'goal': 'answer_user_question',
        'details': {'user_id': 'user456', 'last_message': 'I need help with my bill.'}
    }
    plan1 = planner.create_plan(user_question_goal)
    if plan1:
        print(plan1.model_dump_json(indent=2))

    # --- Test Case 2: Admin Crash Notification ---
    print("\n>>> TEST CASE 2: Notify Admin of Crash <<<")
    crash_goal = {
        'goal': 'notify_admin_about_crash',
        'details': {'error_log': 'CRITICAL: Main process crashed.'}
    }
    plan2 = planner.create_plan(crash_goal)
    if plan2:
        print(plan2.model_dump_json(indent=2))

    # --- Test Case 3: Unknown Goal ---
    print("\n>>> TEST CASE 3: Unknown Goal <<<")
    unknown_goal = {'goal': 'make_coffee'}
    plan3 = planner.create_plan(unknown_goal)
    print(f"Result for unknown goal: {plan3}")
