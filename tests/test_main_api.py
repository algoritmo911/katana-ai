import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Import the app from main.py
# This is a bit tricky because main.py is a script.
# We need to make sure we can import 'app' from it.
# Assuming the project structure allows this import.
from main import app

@pytest.fixture
def client(mocker):
    """
    Pytest fixture to create a TestClient for the FastAPI app.
    It also mocks the global orchestrator_instance.
    """
    # Mock the orchestrator instance that the endpoint uses
    mock_orchestrator = MagicMock()
    mocker.patch('main.orchestrator_instance', mock_orchestrator)

    with TestClient(app) as test_client:
        yield test_client, mock_orchestrator

def test_receive_n8n_webhook_success(client, mocker):
    """
    Tests a successful call to the /webhooks/n8n endpoint.
    """
    # Arrange
    test_client, mock_orchestrator = client
    mocker.patch('os.getenv', return_value="test-api-key")

    headers = {"X-API-Key": "test-api-key"}
    payload = {"task": "Do something awesome"}

    # Act
    response = test_client.post("/webhooks/n8n", headers=headers, json=payload)

    # Assert
    assert response.status_code == 202
    assert response.json() == {"message": "Task accepted"}
    mock_orchestrator.add_tasks.assert_called_once_with(["Do something awesome"])

def test_receive_n8n_webhook_invalid_key(client, mocker):
    """
    Tests a call to the /webhooks/n8n endpoint with an invalid API key.
    """
    # Arrange
    test_client, mock_orchestrator = client
    mocker.patch('os.getenv', return_value="correct-api-key")

    headers = {"X-API-Key": "wrong-api-key"}
    payload = {"task": "This should not be processed"}

    # Act
    response = test_client.post("/webhooks/n8n", headers=headers, json=payload)

    # Assert
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid or missing API Key"}
    mock_orchestrator.add_tasks.assert_not_called()

def test_receive_n8n_webhook_missing_key(client, mocker):
    """
    Tests a call to the /webhooks/n8n endpoint with a missing API key.
    """
    # Arrange
    test_client, mock_orchestrator = client
    mocker.patch('os.getenv', return_value="correct-api-key")

    # No X-API-Key header
    headers = {}
    payload = {"task": "This should also not be processed"}

    # Act
    response = test_client.post("/webhooks/n8n", headers=headers, json=payload)

    # Assert
    assert response.status_code == 403
    # FastAPI returns a more detailed validation error for missing headers
    # We check if the detail contains the expected message.
    assert "Invalid or missing API Key" in response.text
    mock_orchestrator.add_tasks.assert_not_called()
