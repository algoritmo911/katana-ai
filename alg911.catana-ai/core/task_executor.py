# Import the mock service functions
# We need to adjust the path to import from the parent directory's lib
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import memory, nlp, telegram, admin_notifications

class TaskExecutor:
    """
    Executes tasks based on a given goal.
    """
    def __init__(self):
        """
        Initializes the TaskExecutor and its dispatch table.
        The dispatch table maps a goal to a sequence of functions to be executed.
        """
        self.dispatch_table = {
            'answer_user_question': [
                self._retrieve_context,
                self._generate_answer,
                self._send_user_message
            ],
            'notify_admin_about_crash': [
                self._format_report,
                self._send_admin_alert
            ],
            'notify_admin_about_db_failure': [
                self._format_report,
                self._send_admin_alert
            ],
            'investigate_performance_issue': [
                self._format_report,
                self._send_admin_alert
            ]
        }
        self.execution_context = {}

    def execute_goal(self, goal: dict):
        """
        Executes the highest priority goal.
        """
        goal_type = goal.get('goal')
        print(f"\n--- EXECUTING GOAL: {goal_type} ---")
        task_chain = self.dispatch_table.get(goal_type)

        if not task_chain:
            print(f"ERROR: No task chain found for goal: {goal_type}")
            return False

        # Prime the execution context with the goal's details
        self.execution_context = {'goal_details': goal.get('details')}

        for task_function in task_chain:
            try:
                # Each function will read from and write to the context
                task_function()
            except Exception as e:
                print(f"ERROR: Task '{task_function.__name__}' failed for goal '{goal_type}': {e}")
                # Potentially generate a new, high-priority goal to investigate the failure
                return False

        print(f"--- GOAL COMPLETE: {goal_type} ---\n")
        return True

    # --- Task chain methods ---
    # These private methods wrap the service calls.
    # They use self.execution_context to pass data between steps.

    def _retrieve_context(self):
        details = self.execution_context['goal_details']
        user_id = details.get('user_id')
        if not user_id:
            raise ValueError("user_id not found in goal details")

        context = memory.retrieve_full_context(user_id, details)
        self.execution_context['full_context'] = context

    def _generate_answer(self):
        context = self.execution_context.get('full_context')
        if not context:
            raise ValueError("full_context not found in execution context")

        answer = nlp.generate_answer(context)
        self.execution_context['generated_answer'] = answer

    def _send_user_message(self):
        answer = self.execution_context.get('generated_answer')
        user_id = self.execution_context['goal_details'].get('user_id')
        if not answer or not user_id:
            raise ValueError("Answer or user_id missing from execution context")

        telegram.send_message(user_id, answer)

    def _format_report(self):
        details = self.execution_context.get('goal_details')
        if not details:
            raise ValueError("Goal details not found in execution context")

        report = admin_notifications.format_error_report(details)
        self.execution_context['admin_report'] = report

    def _send_admin_alert(self):
        report = self.execution_context.get('admin_report')
        if not report:
            raise ValueError("Admin report not found in execution context")

        admin_notifications.send_admin_notification(report)


if __name__ == '__main__':
    # Example usage for testing
    executor = TaskExecutor()

    # --- Test Case 1: Answer a user question ---
    print(">>> TEST CASE 1: Answer User Question <<<")
    user_question_goal = {
        'goal': 'answer_user_question',
        'priority': 0.9,
        'details': {'id': 2, 'user_id': 'user456', 'last_message': 'I need help with my bill.'},
        'user_id': 'user456',
        'source': 'Supabase'
    }
    executor.execute_goal(user_question_goal)

    # --- Test Case 2: Notify admin about a crash ---
    print("\n>>> TEST CASE 2: Notify Admin of Crash <<<")
    crash_goal = {
        'goal': 'notify_admin_about_crash',
        'priority': 1.0,
        'details': {'error_log': '[2023-10-27T12:00:00Z] CRITICAL: Main process crashed with signal 9.'},
        'source': 'StateMonitor'
    }
    executor.execute_goal(crash_goal)
