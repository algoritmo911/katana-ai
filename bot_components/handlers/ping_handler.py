def handle_ping(command_data, chat_id, logger_func):
    """Handles 'ping' commands."""
    logger_func(f"handle_ping called for chat_id {chat_id} with data: {command_data}")
    return "✅ 'ping' received."
