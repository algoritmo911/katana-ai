import logging
import re
import unicodedata
import queue
import threading
import time
from katana.memory_factory.truth_detector import TruthDetector

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    A module responsible for receiving, cleaning, queuing, and processing
    external information for the Memory Factory. It runs a worker thread
    to process data from a priority queue.
    """

    def __init__(self):
        """Initializes the pipeline, queue, and worker thread components."""
        logger.info("Ingestion Pipeline initializing...")
        self.data_queue = queue.PriorityQueue()
        self.truth_detector = TruthDetector()
        self._stop_event = threading.Event()
        self._worker_thread = None
        logger.info("Ingestion Pipeline initialized successfully.")

    def add_to_queue(self, data: dict, priority: int = 10):
        """Adds a data item to the priority queue."""
        logger.info(f"Adding data to queue with priority {priority}. Current queue size: {self.data_queue.qsize()}")
        self.data_queue.put((priority, data))

    def _worker(self):
        """
        The worker method that runs in a separate thread.
        It continuously gets items from the queue, sanitizes the content,
        and passes the data to the TruthDetector.
        """
        logger.info("Ingestion worker thread started.")
        while not self._stop_event.is_set():
            try:
                # Wait for an item to be available, with a timeout of 1s
                # to allow the loop to check the stop event periodically.
                priority, data = self.data_queue.get(timeout=1)

                logger.info(f"Worker processing item with priority {priority}. Items left: {self.data_queue.qsize()}")

                content = data.get("content")
                if content:
                    # Sanitize the content
                    sanitized_content = self.sanitize_content(content)

                    # Create a new dictionary for the TruthDetector to avoid downstream mutations
                    # of the original data if it were to be stored elsewhere.
                    analysis_data = data.copy()
                    analysis_data["sanitized_content"] = sanitized_content

                    # Pass the processed data to the Truth Detector
                    self.truth_detector.analyze(analysis_data)

                # Mark the task as done for queue management
                self.data_queue.task_done()

            except queue.Empty:
                # This is a normal condition when the queue is empty.
                # The loop will simply continue to the next iteration,
                # checking the stop event again.
                continue
            except Exception as e:
                logger.error(f"An unexpected error occurred in the ingestion worker: {e}", exc_info=True)

        logger.info("Ingestion worker thread has finished its loop.")

    @staticmethod
    def sanitize_content(content: str) -> str:
        """
        Cleans raw string content by removing HTML tags, normalizing unicode,
        and converting to lowercase.
        """
        if not isinstance(content, str):
            logger.warning(f"Sanitize content received non-string type: {type(content)}. Coercing to string.")
            content = str(content)

        clean_content = re.sub(r'<[^>]+>', '', content)
        clean_content = unicodedata.normalize('NFKC', clean_content)
        clean_content = clean_content.lower()

        return clean_content

    def start(self):
        """Starts the background worker thread if it's not already running."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True, name="IngestionWorker")
            self._worker_thread.start()
            logger.info("Ingestion Pipeline worker thread has been started.")
        else:
            logger.warning("Attempted to start Ingestion Pipeline worker thread, but it is already running.")

    def stop(self):
        """Stops the background worker thread gracefully."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.info("Stopping Ingestion Pipeline worker thread...")
            self._stop_event.set()
            # Wait for the thread to finish its current task and exit the loop
            self._worker_thread.join(timeout=5)
            if self._worker_thread.is_alive():
                logger.warning("Ingestion worker thread did not stop within the timeout period.")
            else:
                logger.info("Ingestion Pipeline worker thread stopped successfully.")
        else:
            logger.info("Ingestion Pipeline worker thread is not running.")

    def __str__(self):
        return "IngestionPipeline"
