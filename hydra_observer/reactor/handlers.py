import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def handle_high_cpu(data):
    """Handles high CPU usage events."""
    cpu_percent = data.get("cpu_percent")
    logging.warning(f"High CPU usage detected: {cpu_percent}%")
    # In a real scenario, this could send an alert to Telegram, Discord, etc.

def handle_command_flood(data):
    """Handles command flood events."""
    logging.warning("Command flood detected. Throttling commands.")
    # In a real scenario, this could trigger a mechanism to slow down command processing.

def handle_agent_unresponsive(data):
    """Handles agent unresponsive events."""
    agent_id = data.get("agent_id")
    logging.error(f"Agent {agent_id} is unresponsive. Attempting to restart.")
    # In a real scenario, this would trigger a command to restart the specified agent.

def handle_latency_spike(data):
    """Handles latency spike events."""
    latency_ms = data.get("latency_ms")
    logging.warning(f"Latency spike detected: {latency_ms}ms")
    # In a real scenario, this could send a POST request to an external monitoring system.
