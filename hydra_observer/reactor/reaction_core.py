import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fallback_handler(data):
    """Fallback handler for when a reaction fails."""
    logging.critical(f"A reaction handler failed. Data: {data}")
    # In a real scenario, this would send a notification to a dev channel.

class ReactionCore:
    def __init__(self):
        self._reactions = {}
        self._fallback_handler = fallback_handler

    def register(self, event_name, handler):
        """Registers a handler for a specific event."""
        if event_name not in self._reactions:
            self._reactions[event_name] = []
        self._reactions[event_name].append(handler)
        logging.info(f"Registered handler for event: {event_name}")

    def trigger(self, event_name, data=None):
        """Triggers all handlers for a specific event."""
        if event_name in self._reactions:
            logging.info(f"Triggering event: {event_name} with data: {data}")
            for handler in self._reactions[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    logging.error(f"Error executing handler for event {event_name}: {e}")
                    self._fallback_handler({"event_name": event_name, "error": str(e), "data": data})
        else:
            logging.warning(f"No handlers registered for event: {event_name}")

# Global instance of the ReactionCore
reaction_core = ReactionCore()
