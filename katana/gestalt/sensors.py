import logging
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable

logger = logging.getLogger(__name__)


class BaseSensor(ABC, threading.Thread):
    """
    Abstract base class for all sensors.
    Each sensor runs in its own thread.
    """

    def __init__(self, sensor_id: str, callback: Callable[[str, str], None]):
        super().__init__(daemon=True)
        self.sensor_id = sensor_id
        self.callback = callback
        self._stop_event = threading.Event()

    @abstractmethod
    def poll(self):
        """
        The main polling logic for the sensor. This method should be
        implemented by subclasses to read from their specific data source.
        It should be a blocking or looping call that periodically checks for data.
        """
        pass

    def run(self):
        """The main entry point for the thread."""
        logger.info(f"Starting sensor: {self.sensor_id}")
        self.poll()
        logger.info(f"Sensor stopped: {self.sensor_id}")

    def stop(self):
        """Signals the sensor's polling loop to stop."""
        logger.info(f"Stopping sensor: {self.sensor_id}")
        self._stop_event.set()


class FileSensor(BaseSensor):
    """
    A sensor that monitors a file for new lines (tails a file).
    """

    def __init__(self, sensor_id: str, callback: Callable[[str, str], None], file_path: str, poll_interval: float = 0.5):
        super().__init__(sensor_id, callback)
        self.file_path = file_path
        self.poll_interval = poll_interval

    def poll(self):
        """Tails the specified file, calling the callback for each new line."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                # Seek to the end of the file
                file.seek(0, 2)

                while not self._stop_event.is_set():
                    line = file.readline()
                    if not line:
                        time.sleep(self.poll_interval)
                        continue

                    # We have a new line, process it
                    self.callback(self.sensor_id, line.strip())

        except FileNotFoundError:
            logger.error(f"[{self.sensor_id}] File not found: {self.file_path}. Sensor is stopping.")
        except Exception as e:
            logger.error(f"[{self.sensor_id}] An unexpected error occurred: {e}", exc_info=True)


import queue


class SensorHub:
    """
    Manages all active sensors and funnels their data into a central queue.
    """

    def __init__(self):
        self.sensors = {}
        self.data_queue = queue.Queue()
        self.lock = threading.Lock()

    def get_data_callback(self) -> Callable[[str, str], None]:
        """
        Returns a callback function for sensors to push data into the hub's queue.
        """
        def callback(sensor_id: str, data: str):
            self.data_queue.put((sensor_id, data))
        return callback

    def register_sensor(self, sensor: BaseSensor):
        """Adds a new sensor to the hub."""
        with self.lock:
            if sensor.sensor_id in self.sensors:
                logger.warning(f"Sensor with ID '{sensor.sensor_id}' is already registered.")
                return
            logger.info(f"Registering sensor: {sensor.sensor_id}")
            self.sensors[sensor.sensor_id] = sensor

    def start_all(self):
        """Starts all registered sensors."""
        with self.lock:
            if not self.sensors:
                logger.warning("No sensors registered to start.")
                return
            logger.info("Starting all registered sensors...")
            for sensor_id, sensor in self.sensors.items():
                if not sensor.is_alive():
                    sensor.start()
                else:
                    logger.info(f"Sensor '{sensor_id}' is already running.")

    def stop_all(self):
        """Stops all registered sensors and waits for them to terminate."""
        with self.lock:
            logger.info("Stopping all sensors...")
            for sensor in self.sensors.values():
                sensor.stop()

            # Wait for all threads to finish
            for sensor in self.sensors.values():
                sensor.join()
            logger.info("All sensors have been stopped.")
