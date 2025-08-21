import unittest
import sys
import os
import time
import threading
from pathlib import Path
from unittest.mock import MagicMock

# Adjust path to make katana modules importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.gestalt.sensors import SensorHub, FileSensor

class TestSensorsAndHub(unittest.TestCase):

    def setUp(self):
        self.test_file_path = "test_sensor_file.log"
        # Ensure the file is clean before each test
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    def tearDown(self):
        # Clean up the file after each test
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    def test_file_sensor_reads_new_lines(self):
        """Test that the FileSensor can read new lines appended to a file."""
        # Arrange
        hub = SensorHub()
        # Create a mock callback to check if the data is received
        mock_callback = hub.get_data_callback()

        # Create the sensor
        sensor = FileSensor(
            sensor_id="test_file_sensor",
            callback=mock_callback,
            file_path=self.test_file_path,
            poll_interval=0.01 # Poll quickly for the test
        )

        # Create the file first so the sensor can open it
        with open(self.test_file_path, "w") as f:
            f.write("")

        # Act
        # Start the sensor in a separate thread
        sensor.start()

        # Give the sensor a moment to start up and open the file
        time.sleep(0.1)

        # Write to the file
        with open(self.test_file_path, "a") as f:
            f.write("first line\n")
            f.write("second line\n")

        # Give the sensor time to read the new lines
        time.sleep(0.1)

        # Stop the sensor to clean up the thread
        sensor.stop()
        sensor.join()

        # Assert
        # Check the queue in the hub
        self.assertEqual(hub.data_queue.qsize(), 2)

        # Verify the content of the queue
        first_item = hub.data_queue.get()
        second_item = hub.data_queue.get()

        self.assertEqual(first_item, ("test_file_sensor", "first line"))
        self.assertEqual(second_item, ("test_file_sensor", "second line"))

    def test_hub_manages_multiple_sensors(self):
        """Test that the SensorHub can start and stop multiple sensors."""
        # Arrange
        hub = SensorHub()

        # Create two mock sensors
        mock_sensor_1 = MagicMock(spec=FileSensor)
        mock_sensor_1.sensor_id = "mock_1"
        mock_sensor_1.is_alive.return_value = False

        mock_sensor_2 = MagicMock(spec=FileSensor)
        mock_sensor_2.sensor_id = "mock_2"
        mock_sensor_2.is_alive.return_value = False

        hub.register_sensor(mock_sensor_1)
        hub.register_sensor(mock_sensor_2)

        # Act
        hub.start_all()

        # Assert start calls
        mock_sensor_1.start.assert_called_once()
        mock_sensor_2.start.assert_called_once()

        # Act
        hub.stop_all()

        # Assert stop calls
        mock_sensor_1.stop.assert_called_once()
        mock_sensor_2.stop.assert_called_once()
        mock_sensor_1.join.assert_called_once()
        mock_sensor_2.join.assert_called_once()

if __name__ == '__main__':
    unittest.main()
