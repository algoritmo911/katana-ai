import shared_config

log_event = shared_config.log_event
STATUS_LOGGER_LOG_PREFIX = "[StatusLogger]"

def log_status(status):
    """
    Logs a status message.
    """
    log_event(f"Status: {status}", "info", STATUS_LOGGER_LOG_PREFIX)
    # Add status logging logic here
    pass
