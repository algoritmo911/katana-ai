import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from main import app, task_queue_service
import uuid
from katana.task_queue.models import TaskStatus

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_task_queue_for_main_tests():
    mock_service = MagicMock()

    async def add_task_to_queue_mock(*args, **kwargs):
        mock_task = MagicMock()
        mock_task.id = uuid.uuid4()
        return mock_task

    async def get_task_status_mock(task_id):
        if task_id == uuid.UUID("00000000-0000-0000-0000-000000000000"):
            return None
        return TaskStatus.COMPLETED

    mock_service.add_task_to_queue = AsyncMock(side_effect=add_task_to_queue_mock)
    mock_service.get_task_status = AsyncMock(side_effect=get_task_status_mock)

    with patch("main.task_queue_service", mock_service) as p:
        yield mock_service

def test_add_task_endpoint(mock_task_queue_for_main_tests):
    task_name = "example_task"
    args = [5, 10]
    response = client.post("/task", json={"task_name": task_name, "args": args})

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Task accepted"
    assert "task_id" in data
    assert data["task_name"] == task_name
    mock_task_queue_for_main_tests.add_task_to_queue.assert_called_once()

def test_get_task_status_endpoint(mock_task_queue_for_main_tests):
    task_id = uuid.uuid4()

    response = client.get(f"/task/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == str(task_id)
    assert data["status"] == "COMPLETED"
    mock_task_queue_for_main_tests.get_task_status.assert_called_once_with(task_id)

def test_get_task_status_not_found(mock_task_queue_for_main_tests):
    task_id = uuid.UUID("00000000-0000-0000-0000-000000000000")

    response = client.get(f"/task/{task_id}")

    assert response.status_code == 404
    mock_task_queue_for_main_tests.get_task_status.assert_called_once_with(task_id)

def test_add_task_not_allowed(mock_task_queue_for_main_tests):
    task_name = "not_allowed_task"
    response = client.post("/task", json={"task_name": task_name})
    assert response.status_code == 400
    mock_task_queue_for_main_tests.add_task_to_queue.assert_not_called()