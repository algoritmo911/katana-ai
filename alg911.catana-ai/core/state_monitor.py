import os
import datetime
from supabase import create_client, Client

# --- Configuration ---
# In a production environment, these should be set as actual environment variables
# and not hardcoded in the script.
SUPABASE_URL = "https://pmcaojgdrszvujvwzxrc.supabase.co"
SUPABASE_KEY = "B5SWTeDo6erOovVa" # This should be the service role key

# Assuming the base directory for the agent is one level up from 'core'
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS_LOG_FILE = os.path.join(AGENT_DIR, "katana_events.log")

class StateMonitor:
    """
    Monitors the state of the Katana agent by checking various sources.
    """
    def __init__(self):
        """
        Initializes the StateMonitor and the Supabase client.
        """
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Test connection
            # Note: Supabase Python client doesn't have a direct .ping() or .health()
            # A common way to test is to perform a simple, low-impact query.
            self.supabase.table('users').select('id', head=True).execute()
        except Exception as e:
            print(f"CRITICAL: Failed to initialize Supabase client: {e}")
            self.supabase = None

    def _check_unresolved_tasks_from_db(self):
        """
        Scans Supabase for dialogues with unresolved tasks or unanswered questions.

        Assumption: There is a 'dialogues' table with the following columns:
        - 'id': unique identifier for the dialogue
        - 'user_id': the user participating in the dialogue
        - 'last_message_timestamp': timestamp of the last message
        - 'last_message_from': 'user' or 'agent'
        - 'status': e.g., 'open', 'resolved', 'needs_attention'

        This function looks for dialogues where the last message was from a 'user'
        and it's older than 1 hour.
        """
        if not self.supabase:
            return []

        try:
            one_hour_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()

            # Query for dialogues where the last message is from the user and older than an hour
            # or status is 'needs_attention'
            response = self.supabase.table('dialogues').select('*').or_(
                f'and(last_message_from.eq.user,last_message_timestamp.lt.{one_hour_ago})',
                'status.eq.needs_attention'
            ).execute()

            if response.data:
                return response.data
            return []
        except Exception as e:
            # This can happen if the table 'dialogues' doesn't exist.
            # We'll log this as a system-level issue but not crash.
            print(f"ERROR: Could not query Supabase for unresolved tasks: {e}")
            return [{'error': 'db_query_failed', 'details': str(e)}]


    def _check_logs_for_errors(self):
        """
        Scans the event log for critical errors or repeated warnings.
        """
        critical_errors = []
        if not os.path.exists(EVENTS_LOG_FILE):
            return critical_errors

        try:
            with open(EVENTS_LOG_FILE, 'r') as f:
                for line in f:
                    if "CRITICAL" in line.upper() or "ERROR" in line.upper():
                        critical_errors.append(line.strip())
            return critical_errors
        except Exception as e:
            print(f"ERROR: Could not read log file {EVENTS_LOG_FILE}: {e}")
            return [{'error': 'log_read_failed', 'details': str(e)}]

    def _check_performance_metrics(self):
        """
        Analyzes telemetry for performance issues.
        This is a mock implementation.
        """
        # In a real scenario, this would fetch data from a monitoring service
        # like Prometheus, Datadog, etc.
        # For now, we simulate a potential issue.
        import random
        if random.random() < 0.1: # 10% chance of a performance issue
            return [{'issue': 'high_response_time', 'avg_response_ms': random.randint(1500, 3000)}]
        return []

    def check_state(self):
        """
        Runs all state checks and returns a consolidated report.
        """
        state_report = {
            'unresolved_tasks': self._check_unresolved_tasks_from_db(),
            'critical_errors': self._check_logs_for_errors(),
            'performance_issues': self._check_performance_metrics(),
            'report_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        return state_report

if __name__ == '__main__':
    # This allows for direct testing of the StateMonitor
    print("Running StateMonitor check...")
    monitor = StateMonitor()

    # To test DB connection, we need a 'dialogues' table.
    # If it doesn't exist, the check will gracefully fail and report the error.
    # To test log checking, we can create a dummy log file.
    if not os.path.exists(AGENT_DIR):
        os.makedirs(AGENT_DIR)
    with open(EVENTS_LOG_FILE, 'a') as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] CRITICAL: This is a test critical error.\n")

    report = monitor.check_state()
    import json
    print(json.dumps(report, indent=2))
