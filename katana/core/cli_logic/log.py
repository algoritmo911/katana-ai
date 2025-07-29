import datetime

def get_logs(last, error, today):
    """
    Returns mock logs.
    """
    logs = [
        {"level": "INFO", "message": "User logged in", "timestamp": "2023-10-27 10:00:00"},
        {"level": "INFO", "message": "Data processed", "timestamp": "2023-10-27 10:05:00"},
        {"level": "ERROR", "message": "Connection failed", "timestamp": "2023-10-27 10:10:00"},
        {"level": "INFO", "message": "User logged out", "timestamp": "2023-10-27 10:15:00"},
        {"level": "WARNING", "message": "Disk space is low", "timestamp": str(datetime.datetime.now())},
    ]

    if error:
        logs = [log for log in logs if log["level"] == "ERROR"]

    if today:
        today_str = str(datetime.date.today())
        logs = [log for log in logs if today_str in log["timestamp"]]

    return logs[-last:]
