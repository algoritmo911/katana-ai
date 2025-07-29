def get_history(user):
    """
    Returns mock command history.
    """
    history_data = [
        {"user": "jules", "command": "katana status", "timestamp": "2023-10-27 10:00:00"},
        {"user": "jules", "command": "katana log --error", "timestamp": "2023-10-27 10:05:00"},
        {"user": "guest", "command": "katana status", "timestamp": "2023-10-27 10:10:00"},
        {"user": "jules", "command": "katana cancel 123", "timestamp": "2023-10-27 10:15:00"},
    ]

    if user:
        history_data = [entry for entry in history_data if entry["user"] == user]

    return history_data
