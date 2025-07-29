import pytest
from fastapi.testclient import TestClient
from main import app  # Assuming your FastAPI app is in main.py

client = TestClient(app)
API_KEY = "your-secret-api-key"


def test_list_agents_empty():
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert response.json() == {}


def test_register_agent_unauthorized():
    response = client.post("/api/agents/register?agent_id=test", json={"info": "test"})
    assert response.status_code == 403


def test_register_and_list_agent():
    headers = {"X-API-Key": API_KEY}
    response = client.post(
        "/api/agents/register?agent_id=test_agent",
        json={"info": "test"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "agent_id": "test_agent"}

    response = client.get("/api/agents")
    assert response.status_code == 200
    assert "test_agent" in response.json()


def test_deregister_agent():
    headers = {"X-API-Key": API_KEY}
    client.post(
        "/api/agents/register?agent_id=test_agent_2",
        json={"info": "test"},
        headers=headers,
    )
    response = client.post(
        "/api/agents/deregister?agent_id=test_agent_2", headers=headers
    )
    assert response.status_code == 200
    response = client.get("/api/agents")
    assert "test_agent_2" not in response.json()
