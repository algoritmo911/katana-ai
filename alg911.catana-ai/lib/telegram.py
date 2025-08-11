# Mock implementation of Telegram messaging service

def send_message(user_id: str, message: str):
    """
    Simulates sending a message to a user via Telegram.
    """
    print("="*50)
    print(f"SERVICE_CALL: SIMULATING SENDING TELEGRAM MESSAGE")
    print(f"TO: {user_id}")
    print(f"MESSAGE: {message}")
    print("="*50)
    # In a real implementation, this would return True on success, False on failure.
    return True
