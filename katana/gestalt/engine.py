import logging
import threading
import queue

from .sensors import SensorHub, FileSensor
from .emotions import SentimentAnalyzer
from .events import GestaltEvent
from .memory import GraphMemory

logger = logging.getLogger(__name__)

class GestaltEngine:
    """
    The central orchestrator for the Gestalt system.
    This class initializes and connects all the different components,
    including sensors, emotion analysis, memory, and narrative generation.
    """

    def __init__(self):
        logger.info("Initializing Gestalt Engine...")
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sensor_hub = SensorHub()

        # Define some default keywords for entity extraction.
        # In a real application, this would come from a configuration file.
        default_keywords = ['error', 'exception', 'katana', 'n8n', 'database', 'user', 'message']
        self.memory = GraphMemory(entity_keywords=default_keywords)

        self._stop_event = threading.Event()
        self._processing_thread = threading.Thread(target=self._processing_loop, daemon=True)

    def _processing_loop(self):
        """
        The main loop for the engine's event processing thread.
        It pulls raw data from the sensor hub's queue and processes it.
        """
        logger.info("Gestalt processing loop started.")
        while not self._stop_event.is_set():
            try:
                # Wait for data from the queue, with a timeout to allow checking the stop event
                sensor_id, content = self.sensor_hub.data_queue.get(timeout=1.0)
                self._process_sensor_data(sensor_id, content)
                self.sensor_hub.data_queue.task_done()
            except queue.Empty:
                # This is expected, just continue and check the stop event again
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)

        logger.info("Gestalt processing loop stopped.")

    def _process_sensor_data(self, sensor_id: str, content: str):
        """
        This method takes raw data, creates a structured event, enriches it, and stores it.
        """
        logger.debug(f"Processing data from sensor '{sensor_id}': {content}")

        # 1. Create the base event
        try:
            base_event = GestaltEvent(source_id=sensor_id, content=content)
        except Exception as e:
            logger.error(f"Failed to create GestaltEvent: {e}", exc_info=True)
            return

        # 2. Analyze sentiment to get valence
        valence = self.sentiment_analyzer.get_valence(base_event.content)

        # 3. Create the final, enriched event
        enriched_event = base_event.model_copy(update={'valence': valence})

        logger.info(f"Processed new event: {enriched_event.event_id} | Source: {enriched_event.source_id} | Valence: {enriched_event.valence:.4f}")

        # 4. Store the event in short-term memory
        self.memory.add_event(enriched_event)

    def setup_default_sensors(self, log_file_path: str):
        """
        A helper method to configure some default sensors.
        In a real application, this would be driven by a config file.
        """
        if log_file_path:
            log_sensor = FileSensor(
                sensor_id="main_log_sensor",
                callback=self.sensor_hub.get_data_callback(),
                file_path=log_file_path
            )
            self.sensor_hub.register_sensor(log_sensor)
        else:
            logger.warning("No log file path provided. The default log sensor will not be set up.")

    def start(self):
        """Starts the engine and all its components."""
        if self._processing_thread.is_alive():
            logger.info("Gestalt Engine is already running.")
            return

        logger.info("Starting Gestalt Engine...")
        self._stop_event.clear()
        self.sensor_hub.start_all()
        self._processing_thread.start()
        logger.info("Gestalt Engine started.")

    def stop(self):
        """Stops the engine and all its components gracefully."""
        if not self._processing_thread.is_alive():
            logger.info("Gestalt Engine is not running.")
            return

        logger.info("Stopping Gestalt Engine...")
        # Stop the sensors first, so they don't add more to the queue
        self.sensor_hub.stop_all()

        # Signal the processing thread to stop
        self._stop_event.set()

        # Wait for the processing thread to finish
        self._processing_thread.join()

        logger.info("Gestalt Engine stopped.")
