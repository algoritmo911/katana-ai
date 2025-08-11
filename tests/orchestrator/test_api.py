import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the FastAPI app from your main application file
# Adjust the import path as necessary based on your project structure
from main import app, orchestrator_instance

# Create a client for testing
client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_orchestrator_instance():
    """
    This fixture automatically mocks the global orchestrator_instance for all tests in this file.
    """
    # Create a mock orchestrator that we can inspect
    mock_orchestrator = MagicMock()
    mock_orchestrator.add_tasks = MagicMock()

    # Use patch to replace the global orchestrator_instance in main.py
    # with our mock object for the duration of a test.
    with patch('main.orchestrator_instance', mock_orchestrator) as patched_orchestrator:
        yield patched_orchestrator

def test_n8n_webhook_success(mock_orchestrator_instance):
    """
    Tests the /n8n/webhook endpoint with a valid payload.
    """
    # Arrange
    tasks_payload = {
        "tasks": ["task 1 from webhook", "task 2 from webhook"]
    }

    # Act
    response = client.post("/n8n/webhook", json=tasks_payload)

    # Assert
    assert response.status_code == 202
    assert response.json() == {"message": "Successfully queued 2 tasks."}

    # Check that the orchestrator's add_tasks method was called correctly
    mock_orchestrator_instance.add_tasks.assert_called_once_with(tasks_payload["tasks"])

def test_n8n_webhook_empty_task_list(mock_orchestrator_instance):
    """
    Tests the /n8n/webhook endpoint with an empty list of tasks.
    The endpoint should still accept the request (202) but not process it.
    """
    # Arrange
    tasks_payload = {
        "tasks": []
    }

    # Act
    response = client.post("/n8n/webhook", json=tasks_payload)

    # Assert
    assert response.status_code == 202 # The endpoint is set to return 202 on success.
    assert response.json() == {"message": "Received empty task list. No action taken."}

    # Ensure add_tasks was not called
    mock_orchestrator_instance.add_tasks.assert_not_called()

def test_n8n_webhook_invalid_payload_missing_key():
    """
    Tests the webhook with a payload that is missing the 'tasks' key.
    FastAPI and Pydantic should handle this automatically.
    """
    # Arrange
    invalid_payload = {
        "some_other_key": ["a", "b"]
    }

    # Act
    response = client.post("/n8n/webhook", json=invalid_payload)

    # Assert
    assert response.status_code == 422 # Unprocessable Entity
    # The response body should contain details about the validation error
    assert "detail" in response.json()
    # Pydantic v2 error messages are more user-friendly.
    assert "Field required" in response.json()['detail'][0]['msg']
    assert response.json()['detail'][0]['loc'] == ['body', 'tasks']


def test_n8n_webhook_invalid_payload_wrong_type():
    """
    Tests the webhook with a payload where 'tasks' is not a list of strings.
    """
    # Arrange
    invalid_payload = {
        "tasks": "this is not a list"
    }

    # Act
    response = client.post("/n8n/webhook", json=invalid_payload)

    # Assert
    assert response.status_code == 422 # Unprocessable Entity
    assert "detail" in response.json()
    # Pydantic v2 error messages are more user-friendly.
    assert "Input should be a valid list" in response.json()['detail'][0]['msg']
    assert response.json()['detail'][0]['loc'] == ['body', 'tasks']
