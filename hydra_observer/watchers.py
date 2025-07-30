import logging
import time
from hydra_observer.reactor.reaction_core import reaction_core
from hydra_observer.reactor.handlers import handle_command_flood, handle_agent_unresponsive, handle_latency_spike

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Register reactions
reaction_core.register("command_flood", handle_command_flood)
reaction_core.register("agent_unresponsive", handle_agent_unresponsive)
reaction_core.register("latency_spike", handle_latency_spike)

def watch_for_critical_events():
    """Watches for critical events. Placeholder for now."""
    logging.info("Watcher started. No critical events to watch for yet.")
    while True:
        # In the future, this could check for things like:
        # - High error rates in logs
        # - Specific keywords in logs
        # - Service health checks

        # Placeholder for command flood detection
        # reaction_core.trigger("command_flood", {})

        # Placeholder for agent unresponsive detection
        # reaction_core.trigger("agent_unresponsive", {"agent_id": "some_agent"})

        # Placeholder for latency spike detection
        # reaction_core.trigger("latency_spike", {"latency_ms": 500})

        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    logging.info("Starting watchers.")
    watch_for_critical_events()
