import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReactionCore:
    def __init__(self):
        self._reactions = {}

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
        else:
            logging.warning(f"No handlers registered for event: {event_name}")

# Global instance of the ReactionCore
reaction_core = ReactionCore()
