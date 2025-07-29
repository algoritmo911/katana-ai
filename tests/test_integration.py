import requests
import time
import subprocess
import pytest

@pytest.fixture(scope="function")
def docker_compose():
    try:
        print("Starting docker-compose...")
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
        # Give the services time to start up
        time.sleep(10)
        yield
    finally:
        print("Stopping docker-compose...")
        subprocess.run(["docker", "compose", "down"], check=True)

def test_add_and_get_tasks(docker_compose):
    # Add tasks to the task manager
    tasks = ["task1", "task2", "task3"]
    response = requests.post("http://localhost:8001/tasks", json=tasks)
    assert response.status_code == 200
    assert response.json() == {"message": "Tasks added successfully"}

    # Wait for the agent interactor to process the tasks
    time.sleep(5)

    # Get metrics from the metrics service
    response = requests.get("http://localhost:8002/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) == 3
    assert metrics[0]["task"] == "task1"
    assert metrics[0]["success"] == True
    assert metrics[1]["task"] == "task2"
    assert metrics[1]["success"] == True
    assert metrics[2]["task"] == "task3"
    assert metrics[2]["success"] == True

def test_add_failing_task(docker_compose):
    # Add a failing task
    tasks = ["fail task"]
    response = requests.post("http://localhost:8001/tasks", json=tasks)
    assert response.status_code == 200

    # Wait for the agent interactor to process the task
    time.sleep(5)

    # Get metrics from the metrics service
    response = requests.get("http://localhost:8002/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) == 1
    assert metrics[0]["task"] == "fail task"
    assert metrics[0]["success"] == False
