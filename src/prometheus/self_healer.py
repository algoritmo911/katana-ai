import json
from typing import List, Dict, Any

# Define a threshold for what constitutes a high failure rate.
FAILURE_RATE_THRESHOLD = 0.5  # 50%
MIN_TASKS_FOR_ANALYSIS = 3    # Don't analyze rounds with too few tasks.

def analyze_logs_and_generate_tasks(log_file: str) -> List[Dict[str, Any]]:
    """
    Analyzes the orchestrator log file to identify performance issues
    and generates tasks to address them.

    Args:
        log_file: Path to the orchestrator's JSON log file.

    Returns:
        A list of new tasks for the orchestrator to execute.
    """
    new_tasks = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the log file doesn't exist or is invalid, there's nothing to analyze.
        return []

    if not isinstance(log_data, list) or not log_data:
        return []

    # Analyze the most recent round first.
    last_round = log_data[-1]

    tasks_processed = last_round.get('tasks_processed_count', 0)
    failed_tasks = last_round.get('failed_tasks_count', 0)
    success_rate = last_round.get('success_rate', 1.0)
    round_timestamp = last_round.get('timestamp')

    # Check if the round meets the criteria for generating a self-healing task.
    if tasks_processed >= MIN_TASKS_FOR_ANALYSIS and success_rate < (1.0 - FAILURE_RATE_THRESHOLD):
        print(f"[Prometheus] Detected high failure rate ({failed_tasks}/{tasks_processed}) in round {round_timestamp}. Generating self-healing task.")

        # Identify the failed task types for better diagnostics.
        failed_task_details = [
            result['task'] for result in last_round.get('results_summary', []) if not result['success']
        ]

        task_id = f"prometheus_heal_{round_timestamp}"
        task_description = (
            f"High failure rate detected in round from {round_timestamp}. "
            f"{failed_tasks} out of {tasks_processed} tasks failed. "
            f"Analyze failed tasks to identify root cause and propose a patch."
        )

        new_task = {
            "id": task_id,
            "type": "self_healing_diagnostics",
            "description": task_description,
            "details": {
                "failed_round_timestamp": round_timestamp,
                "failed_tasks_summary": failed_task_details
            },
            "source": "prometheus_self_healer",
            "status": "pending"
        }
        new_tasks.append(new_task)

    return new_tasks

if __name__ == '__main__':
    # Example Usage:
    # Create a dummy log file for the test.
    dummy_log_file = 'orchestrator_log.json'

    # --- Test Case 1: High Failure Rate ---
    print("--- Testing with high failure rate ---")
    high_failure_log = [
        {
            "timestamp": "2025-08-11T12:00:00Z",
            "tasks_processed_count": 5,
            "failed_tasks_count": 3,
            "success_rate": 0.4,
            "results_summary": [
                {"task": {"type": "n8n_workflow_generation"}, "success": True},
                {"task": {"type": "text_generation"}, "success": False, "details": "Timeout"},
                {"task": {"type": "n8n_workflow_generation"}, "success": True},
                {"task": {"type": "text_generation"}, "success": False, "details": "API key invalid"},
                {"task": {"type": "text_generation"}, "success": False, "details": "Model overload"},
            ]
        }
    ]
    with open(dummy_log_file, 'w') as f:
        json.dump(high_failure_log, f)

    generated_tasks = analyze_logs_and_generate_tasks(dummy_log_file)
    print("Generated tasks:")
    print(json.dumps(generated_tasks, indent=2))
    assert len(generated_tasks) == 1
    assert generated_tasks[0]['type'] == 'self_healing_diagnostics'

    # --- Test Case 2: Low Failure Rate ---
    print("\n--- Testing with low failure rate ---")
    low_failure_log = [
        {
            "timestamp": "2025-08-11T13:00:00Z",
            "tasks_processed_count": 5,
            "failed_tasks_count": 1,
            "success_rate": 0.8
        }
    ]
    with open(dummy_log_file, 'w') as f:
        json.dump(low_failure_log, f)

    generated_tasks = analyze_logs_and_generate_tasks(dummy_log_file)
    print("Generated tasks:")
    print(json.dumps(generated_tasks, indent=2))
    assert len(generated_tasks) == 0

    # --- Test Case 3: Too few tasks ---
    print("\n--- Testing with too few tasks ---")
    too_few_tasks_log = [
        {
            "timestamp": "2025-08-11T14:00:00Z",
            "tasks_processed_count": 2,
            "failed_tasks_count": 2,
            "success_rate": 0.0
        }
    ]
    with open(dummy_log_file, 'w') as f:
        json.dump(too_few_tasks_log, f)

    generated_tasks = analyze_logs_and_generate_tasks(dummy_log_file)
    print("Generated tasks:")
    print(json.dumps(generated_tasks, indent=2))
    assert len(generated_tasks) == 0

    import os
    os.remove(dummy_log_file)
    print(f"\nCleaned up {dummy_log_file}")
