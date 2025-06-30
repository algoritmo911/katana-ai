# src/connectors/core_connector.py
import json
import time
from typing import Dict, Any, Tuple

def call_sc_core(task_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Simulates a call to the SC (Smart Contract or System Core) Core.

    Args:
        task_data: A dictionary containing the task details.

    Returns:
        A tuple containing:
            - bool: True if the call was successful (simulated), False otherwise.
            - Dict[str, Any]: A dictionary with the result or error details.
    """
    print(f"[CoreConnector] Received task data: {json.dumps(task_data)}")
    task_id = task_data.get("id", "unknown_task")

    # Simulate some processing time
    time.sleep(0.1) # Simulate a quick call

    # Simulate different outcomes based on task type or other conditions
    if task_data.get("type") == "critical_operation":
        # Simulate a failure for a specific type of task
        print(f"[CoreConnector] Simulating failure for critical task: {task_id}")
        return False, {"task_id": task_id, "status": "failed", "error": "Simulated SC Core error for critical operation"}
    else:
        # Simulate a successful call
        print(f"[CoreConnector] Simulating success for task: {task_id}")
        return True, {"task_id": task_id, "status": "completed", "result": f"Mock result for task {task_id}", "timestamp": time.time()}

if __name__ == '__main__':
    print("Testing CoreConnector...")

    task1_data = {"id": "task_abc_123", "type": "generic_processing", "payload": {"value": 42}}
    success1, result1 = call_sc_core(task1_data)
    print(f"Task 1 ({task1_data['id']}): Success = {success1}, Result = {json.dumps(result1)}")

    task2_data = {"id": "task_xyz_789", "type": "critical_operation", "payload": {"action": "deploy_contract"}}
    success2, result2 = call_sc_core(task2_data)
    print(f"Task 2 ({task_data['id']}): Success = {success2}, Result = {json.dumps(result2)}")

    task3_data = {"id": "task_def_456", "type": "data_query", "payload": {"query": "SELECT * FROM table"}}
    success3, result3 = call_sc_core(task3_data)
    print(f"Task 3 ({task3_data['id']}): Success = {success3}, Result = {json.dumps(result3)}")
