import shared_config

log_event = shared_config.log_event
COMMAND_HANDLER_LOG_PREFIX = "[CommandHandler]"

def handle_command(command):
    """
    Handles a single command.
    """
    log_event(f"Handling command: {command}", "info", COMMAND_HANDLER_LOG_PREFIX)
    # Add command handling logic here
    pass
