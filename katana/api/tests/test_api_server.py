import pytest
import logging
import json
from pathlib import Path
from fastapi.testclient import TestClient
from unittest import mock
import os # For checking environment variables, if any tests need it for setup

# Assuming katana.api.server is where your FastAPI app instance is
from katana.api.server import app, LOG_LINE_REGEX # Import app and other necessary items
# Import items from logging_config that tests might need to reference or manipulate
from katana.logging_config import (
    DEFAULT_LOG_FILE_NAME,
    DEFAULT_LOGGER_NAME,
    setup_logging as setup_katana_logging # Alias for clarity
)

# TestClient for making requests to the FastAPI app
client = TestClient(app)

@pytest.fixture
def mock_log_file(tmp_path, monkeypatch):
    """
    Fixture to create a temporary log file and mock LOG_FILE_PATH in katana.api.server.
    It also ensures Katana's logging is re-initialized to use this temp file.
    """
    temp_log_dir = tmp_path / "logs_test"
    temp_log_dir.mkdir()
    temp_log_file = temp_log_dir / "test_katana_events.log"

    # Patch the LOG_FILE_PATH constant in the server module where it's used by endpoints
    monkeypatch.setattr("katana.api.server.LOG_FILE_PATH", temp_log_file)

    # Also re-initialize Katana's logging to use this temp file for its handlers
    # This ensures that if the API tries to read info from the logger's handlers, it's consistent.
    # And more importantly, that log messages generated *during tests* go to this temp file.
    setup_katana_logging(log_level=logging.DEBUG, log_file_path=str(temp_log_file))

    yield temp_log_file # The test will use this path to write/check log content

    # Cleanup: TestClient might have open file handlers via the app's logger.
    # It's good practice to ensure all handlers are closed before removing the file.
    app_logger = logging.getLogger(DEFAULT_LOGGER_NAME)
    for handler in list(app_logger.handlers): # Iterate over a copy
        handler.close()
        app_logger.removeHandler(handler) # Remove to be sure

    if temp_log_file.exists():
        temp_log_file.unlink()
    if temp_log_dir.exists():
        # Only remove if empty, or handle more robustly if needed
        if not any(temp_log_dir.iterdir()):
             temp_log_dir.rmdir()

# Test Cases
def test_get_log_status_default(mock_log_file): # Use mock_log_file to ensure consistent path
    """Test the default status of the logging system."""
    # Ensure logging is set to a known state for this test, using the mocked file
    setup_katana_logging(log_level=logging.INFO, log_file_path=str(mock_log_file))

    response = client.get("/api/logs/status")
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == "INFO"
    assert Path(data["log_file"]).name == mock_log_file.name

def test_set_log_level(mock_log_file):
    """Test setting and retrieving the log level."""
     # Set initial level for this test context
    setup_katana_logging(log_level=logging.INFO, log_file_path=str(mock_log_file))

    # Set to DEBUG
    response_set_debug = client.post("/api/logs/level", json={"level": "DEBUG"})
    assert response_set_debug.status_code == 200
    assert response_set_debug.json()["message"] == "Log level set to DEBUG"

    response_status_debug = client.get("/api/logs/status")
    assert response_status_debug.status_code == 200
    assert response_status_debug.json()["level"] == "DEBUG"

    # Test with an invalid level
    response_set_invalid = client.post("/api/logs/level", json={"level": "INVALID_LEVEL"})
    assert response_set_invalid.status_code == 400
    assert "Invalid log level" in response_set_invalid.json()["detail"]

    # Restore to INFO (or original default for logging_config)
    response_set_info = client.post("/api/logs/level", json={"level": "INFO"})
    assert response_set_info.status_code == 200
    response_status_info = client.get("/api/logs/status")
    assert response_status_info.json()["level"] == "INFO"


def test_get_logs_empty(mock_log_file):
    """Test retrieving logs when the log file is empty."""
    # mock_log_file fixture ensures the file exists but is empty initially for this part
    assert mock_log_file.exists()
    assert mock_log_file.read_text() == ""

    response = client.get("/api/logs")
    assert response.status_code == 200
    assert response.json() == []

def test_get_logs_with_content(mock_log_file):
    """Test retrieving logs when the log file has content."""
    log_lines = [
        "INFO 2023-01-01 10:00:00,000 - module1 - Message 1\n",
        "DEBUG 2023-01-01 10:05:00,000 - module2 - Message 2 with debug\n",
        "ERROR 2023-01-01 10:10:00,000 - module1 - Error message 3\n",
    ]
    with open(mock_log_file, "w") as f:
        f.writelines(log_lines)

    response = client.get("/api/logs")
    assert response.status_code == 200
    logs_data = response.json()
    assert len(logs_data) == 3
    # Logs are returned newest first (so, reversed order of log_lines)
    assert logs_data[0]["message"] == "Error message 3"
    assert logs_data[0]["level"] == "ERROR"
    assert logs_data[0]["module"] == "module1"
    assert logs_data[1]["message"] == "Message 2 with debug"
    assert logs_data[1]["level"] == "DEBUG"
    assert logs_data[2]["message"] == "Message 1"
    assert logs_data[2]["level"] == "INFO"

def test_get_logs_pagination(mock_log_file):
    """Test pagination of log entries."""
    # Create 7 log entries (newest will be "Message 7")
    log_entries_content = []
    for i in range(1, 8): # 7 entries
        log_entries_content.append(f"INFO 2023-01-01 10:0{i}:00,000 - PaginMod - Message {i}\n")

    with open(mock_log_file, "w") as f:
        f.writelines(log_entries_content)

    # Page 1, limit 3 (should get Messages 7, 6, 5)
    response_page1 = client.get("/api/logs?page=1&limit=3")
    assert response_page1.status_code == 200
    data_page1 = response_page1.json()
    assert len(data_page1) == 3
    assert data_page1[0]["message"] == "Message 7"
    assert data_page1[1]["message"] == "Message 6"
    assert data_page1[2]["message"] == "Message 5"

    # Page 2, limit 3 (should get Messages 4, 3, 2)
    response_page2 = client.get("/api/logs?page=2&limit=3")
    assert response_page2.status_code == 200
    data_page2 = response_page2.json()
    assert len(data_page2) == 3
    assert data_page2[0]["message"] == "Message 4"
    assert data_page2[1]["message"] == "Message 3"
    assert data_page2[2]["message"] == "Message 2"

    # Page 3, limit 3 (should get Message 1)
    response_page3 = client.get("/api/logs?page=3&limit=3")
    assert response_page3.status_code == 200
    data_page3 = response_page3.json()
    assert len(data_page3) == 1
    assert data_page3[0]["message"] == "Message 1"

    # Page 4, limit 3 (should get empty list)
    response_page4 = client.get("/api/logs?page=4&limit=3")
    assert response_page4.status_code == 200
    assert response_page4.json() == []


def test_get_logs_filtering_level(mock_log_file):
    """Test filtering logs by level."""
    log_lines = [
        "INFO 2023-01-01 10:00:00,000 - module.info - Info message\n",
        "DEBUG 2023-01-01 10:05:00,000 - module.debug - Debug message\n",
        "INFO 2023-01-01 10:10:00,000 - module.info2 - Another info message\n",
        "ERROR 2023-01-01 10:15:00,000 - module.error - Error occurred\n",
    ]
    with open(mock_log_file, "w") as f:
        f.writelines(log_lines)

    response = client.get("/api/logs?level=INFO")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    for entry in data:
        assert entry["level"] == "INFO"
    # Newest first:
    assert data[0]["message"] == "Another info message"
    assert data[1]["message"] == "Info message"

def test_get_logs_filtering_search(mock_log_file):
    """Test filtering logs by a search term (case-insensitive)."""
    log_lines = [
        "INFO 2023-01-01 10:00:00,000 - search.mod - Message with UniqueKeyword\n",
        "DEBUG 2023-01-01 10:05:00,000 - search.mod2 - Another message without the keyword\n",
        "ERROR 2023-01-01 10:10:00,000 - search.mod3 - Message with uniquekeyword (lowercase)\n",
    ]
    with open(mock_log_file, "w") as f:
        f.writelines(log_lines)

    response = client.get("/api/logs?search=UniqueKeyword")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Newest first
    assert "uniquekeyword (lowercase)" in data[0]["message"]
    assert "UniqueKeyword" in data[1]["message"]


def test_get_logs_filtering_level_and_search(mock_log_file):
    """Test filtering by both level and search term."""
    log_lines = [
        "INFO 2023-01-01 10:00:00,000 - combo.mod - Info message with TargetWord\n",
        "ERROR 2023-01-01 10:05:00,000 - combo.mod2 - Error message with TargetWord\n",
        "INFO 2023-01-01 10:10:00,000 - combo.mod3 - Just an info message\n",
        "ERROR 2023-01-01 10:15:00,000 - combo.mod4 - Just an error message\n",
        "DEBUG 2023-01-01 10:20:00,000 - combo.mod5 - Debug with TargetWord\n",
    ]
    with open(mock_log_file, "w") as f:
        f.writelines(log_lines)

    # Test 1: Level ERROR, search TargetWord
    response1 = client.get("/api/logs?level=ERROR&search=TargetWord")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1) == 1
    assert data1[0]["level"] == "ERROR"
    assert "TargetWord" in data1[0]["message"]
    assert data1[0]["module"] == "combo.mod2" # This is the newest matching entry

    # Test 2: Level INFO, search TargetWord
    response2 = client.get("/api/logs?level=INFO&search=TargetWord")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 1
    assert data2[0]["level"] == "INFO"
    assert "TargetWord" in data2[0]["message"]
    assert data2[0]["module"] == "combo.mod"

def test_get_logs_file_not_found(monkeypatch):
    """Test behavior when the log file does not exist."""
    non_existent_path = Path("non_existent_log_file_for_test.log")
    if non_existent_path.exists(): # Should not exist, but ensure for test
        non_existent_path.unlink()

    # Patch LOG_FILE_PATH in the server module for this test only
    monkeypatch.setattr("katana.api.server.LOG_FILE_PATH", non_existent_path)

    response = client.get("/api/logs")
    assert response.status_code == 404
    assert "Log file not found" in response.json()["detail"]

# It might be good to add a test for unparseable lines,
# but current server logic logs a warning and skips them.
# This behavior is implicitly covered if we check counts of returned logs
# when mixed with unparseable lines.
# For now, the existing tests cover the main functionality.
