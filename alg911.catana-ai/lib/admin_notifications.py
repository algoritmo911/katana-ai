# Mock implementation of a service to notify administrators

def format_error_report(details: dict):
    """
    Formats a detailed error report for an administrator.
    """
    print("SERVICE_CALL: Formatting error report...")
    report = "KATANA AGENT ALERT\n\n"
    if details.get('error_log'):
        report += f"Type: Crash/Critical Error\n"
        report += f"Log Entry: {details['error_log']}\n"
    elif details.get('error') == 'db_query_failed':
        report += f"Type: Database Failure\n"
        report += f"Details: {details.get('details')}\n"
    elif details.get('issue') == 'high_response_time':
        report += f"Type: Performance Degradation\n"
        report += f"Details: {details}\n"
    else:
        report += f"Type: General Alert\n"
        report += f"Details: {details}\n"
    print("SERVICE_CALL: Report formatted.")
    return report

def send_admin_notification(report: str):
    """
    Simulates sending a notification (e.g., via Slack, PagerDuty, email) to an admin.
    """
    print("="*50)
    print(f"SERVICE_CALL: SIMULATING SENDING ADMIN NOTIFICATION")
    print(f"REPORT:\n{report}")
    print("="*50)
    return True
