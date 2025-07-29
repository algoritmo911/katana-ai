import requests
import time
import subprocess
import pytest
import uuid
import os

@pytest.fixture(scope="function")
def docker_compose():
    task_queue_name = str(uuid.uuid4())
    result_queue_name = str(uuid.uuid4())

    env = os.environ.copy()
    env["TASK_QUEUE_NAME"] = task_queue_name
    env["RESULT_QUEUE_NAME"] = result_queue_name

    try:
        print("Starting docker-compose...")
        subprocess.run(["docker", "compose", "up", "-d"], check=True, env=env)
        # Give the services time to start up
        time.sleep(10)
        yield task_queue_name, result_queue_name
    finally:
        print("Stopping docker-compose...")
        subprocess.run(["docker", "compose", "down", "-v", "--remove-orphans"], check=True, env=env)

def test_add_and_get_tasks(docker_compose):
    task_queue_name, result_queue_name = docker_compose
    # Add tasks to the task manager
    tasks = ["task1", "task2", "task3"]
    response = requests.post(f"http://localhost:8001/tasks?queue_name={task_queue_name}", json=tasks)
    assert response.status_code == 200
    assert response.json() == {"message": "Tasks added successfully"}

    # Wait for the agent interactor to process the tasks
    time.sleep(5)

    # Get metrics from the metrics service
    response = requests.get(f"http://localhost:8002/metrics?queue_name={task_queue_name}")
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
    task_queue_name, result_queue_name = docker_compose
    # Add a failing task
    tasks = ["fail task"]
    response = requests.post(f"http://localhost:8001/tasks?queue_name={task_queue_name}", json=tasks)
    assert response.status_code == 200

    # Wait for the agent interactor to process the task
    time.sleep(5)

    # Get metrics from the metrics service
    response = requests.get(f"http://localhost:8002/metrics?queue_name={task_queue_name}")
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) == 1
    assert metrics[0]["task"] == "fail task"
    assert metrics[0]["success"] == False
