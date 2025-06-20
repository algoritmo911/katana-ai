import pytest
import json
import os

MOCK_API_COMMANDS_FILE = "mock_api_katana.commands.json"
MOCK_API_MEMORY_FILE = "mock_api_katana_memory.json"
MOCK_API_EVENTS_LOG_FILE = "mock_api_katana_events.log"

from backend import socket_handlers as socket_handlers_module_for_api
from katana_ui_server import app as flask_app

@pytest.fixture(scope='function')
def app_with_mocked_paths(monkeypatch):
    for f_path in [MOCK_API_COMMANDS_FILE, MOCK_API_MEMORY_FILE, MOCK_API_EVENTS_LOG_FILE]:
        if os.path.exists(f_path):
            os.remove(f_path)

    with open(MOCK_API_EVENTS_LOG_FILE, 'w') as f:
        f.write("log entry 1\nlog entry 2\n")

    with open(MOCK_API_MEMORY_FILE, 'w') as f:
        json.dump({"test_key": "test_value"}, f)

    with open(MOCK_API_COMMANDS_FILE, 'w') as f:
        json.dump([{"action": "pending_action", "processed": False}], f)

    monkeypatch.setattr(socket_handlers_module_for_api, 'KATANA_COMMANDS_JSON', MOCK_API_COMMANDS_FILE)
    monkeypatch.setattr(socket_handlers_module_for_api, 'KATANA_MEMORY_JSON', MOCK_API_MEMORY_FILE)
    monkeypatch.setattr('katana_ui_server.KATANA_EVENTS_LOG', MOCK_API_EVENTS_LOG_FILE, raising=False)
    monkeypatch.setattr('katana_ui_server.last_log_size', 0, raising=False)

    flask_app.config.update({
        "TESTING": True,
    })
    yield flask_app

    for f_path in [MOCK_API_COMMANDS_FILE, MOCK_API_MEMORY_FILE, MOCK_API_EVENTS_LOG_FILE]:
        if os.path.exists(f_path):
            os.remove(f_path)

@pytest.fixture
def client(app_with_mocked_paths):
    return app_with_mocked_paths.test_client()

def test_api_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "katana_memory" in data
    assert data["katana_memory"] == {"test_key": "test_value"}
    assert "pending_commands_count" in data
    assert data["pending_commands_count"] == 1
    assert "log_file_size" in data
    assert data["log_file_size"] > 0

def test_api_logs_endpoint(client):
    response = client.get("/api/logs")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "logs" in data
    assert isinstance(data["logs"], list)
    assert len(data["logs"]) == 2
    assert data["logs"][0] == "log entry 1"
