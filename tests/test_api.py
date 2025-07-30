import pytest
from fastapi.testclient import TestClient
from katana.api import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/katana/health")
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "ok"
    assert "uptime" in json_response

def test_get_katana_stats():
    response = client.get("/api/katana/stats")
    assert response.status_code == 200
    json_response = response.json()
    assert "uptime" in json_response
    assert "commands_received" in json_response
    assert "last_command_ts" in json_response
    assert "dry_run" in json_response
    assert "build_version" in json_response
    assert "last_command_echo" in json_response
