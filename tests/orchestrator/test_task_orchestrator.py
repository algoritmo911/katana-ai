import unittest
import asyncio
import json
import os
from unittest.mock import AsyncMock, patch, mock_open
from collections import Counter

from src.orchestrator.task_orchestrator import TaskOrchestrator, TaskResult
from src.orchestrator.error_analyzer import ErrorCriticality

# A mock JuliusAgent for testing purposes
class MockJuliusAgent:
    def __init__(self, results_to_return=None):
        self.results_to_return = results_to_return if results_to_return is not None else []
        self.call_count = 0
        self.last_tasks_processed = []

    async def process_tasks(self, tasks: list[str]) -> list[TaskResult]:
        self.call_count += 1
        self.last_tasks_processed = tasks
        if callable(self.results_to_return):
             # If it's a callable, it might be dynamic based on tasks
            return self.results_to_return(tasks)

        # If results_to_return is not callable, it should be a list
        if not self.results_to_return: # Handle empty list case
            return [TaskResult(success=False, details="No mock result configured", task_content=t) for t in tasks]

        # If list is shorter than tasks, cycle through it
        num_tasks = len(tasks)
        return [self.results_to_return[i % len(self.results_to_return)] for i in range(num_tasks)]


class TestTaskOrchestrator(unittest.TestCase):
    def setUp(self):
        self.log_file = "test_orchestrator_log.json"
        # Ensure a clean slate for the log file
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

        self.mock_agent = MockJuliusAgent()
        # Patching of classify_error is removed. Tests will use the actual classify_error.
        self.orchestrator = TaskOrchestrator(agent=self.mock_agent, batch_size=2, max_batch=5, metrics_log_file=self.log_file)

    def tearDown(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def test_initialization(self):
        self.assertEqual(self.orchestrator.batch_size, 2)
        self.assertEqual(len(self.orchestrator.task_queue), 0)
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, 'r') as f:
            loaded_json = json.load(f)
            self.assertEqual(loaded_json, [])

    def test_add_tasks(self):
        self.orchestrator.add_tasks(["task1", "task2"])
        self.assertEqual(len(self.orchestrator.task_queue), 2)
        self.orchestrator.add_tasks(["task3"])
        self.assertEqual(len(self.orchestrator.task_queue), 3)
        self.assertEqual(self.orchestrator.task_queue, ["task1", "task2", "task3"])

    @patch("src.orchestrator.task_orchestrator.time.strftime")
    def test_run_round_successful_tasks(self, mock_strftime):
        mock_strftime.return_value = "2023-10-26T10:00:00+0000"
        self.orchestrator.add_tasks(["task1", "task2", "task3"])

        self.mock_agent.results_to_return = [
            TaskResult(success=True, details="Completed", task_content="task1"),
            TaskResult(success=True, details="Completed", task_content="task2")
        ]

        asyncio.run(self.orchestrator.run_round())

        self.assertEqual(self.mock_agent.call_count, 1)
        self.assertEqual(len(self.orchestrator.task_queue), 1)
        self.assertEqual(self.orchestrator.batch_size, 3)
        self.assertEqual(len(self.orchestrator.metrics_history), 1)

        metric = self.orchestrator.metrics_history[0]
        self.assertEqual(metric['successful_tasks_count'], 2)
        self.assertEqual(metric['failed_tasks_count'], 0)
        self.assertEqual(metric['error_summary_by_criticality'], {})
        self.assertEqual(len(metric['results_summary']), 2)
        self.assertTrue(metric['results_summary'][0]['success'])
        self.assertNotIn('error_classification', metric['results_summary'][0])


        with open(self.log_file, 'r') as f:
            log_data = json.load(f)
        self.assertEqual(len(log_data), 1)
        self.assertEqual(log_data[0]['successful_tasks_count'], 2)


    @patch("src.orchestrator.task_orchestrator.time.strftime")
    def test_run_round_failed_task_classification_integration(self, mock_strftime):
        mock_strftime.return_value = "2023-10-26T11:00:00+0000"
        self.orchestrator.add_tasks(["task_A", "task_B"])
        self.orchestrator.batch_size = 2

        # Now uses actual classify_error, ensure details string matches error_analyzer's keywords
        self.mock_agent.results_to_return = [
            TaskResult(success=True, details="OK", task_content="task_A"),
            TaskResult(success=False, details="API error: limit reached", task_content="task_B") # "api error" is a keyword
        ]

        asyncio.run(self.orchestrator.run_round())

        self.assertEqual(self.orchestrator.batch_size, 1)
        self.assertEqual(len(self.orchestrator.metrics_history), 1)
        metric = self.orchestrator.metrics_history[0]

        self.assertEqual(metric['failed_tasks_count'], 1)
        self.assertEqual(metric['successful_tasks_count'], 1)
        self.assertIn(ErrorCriticality.HIGH.value, metric['error_summary_by_criticality'])
        self.assertEqual(metric['error_summary_by_criticality'][ErrorCriticality.HIGH.value], 1)

        failed_task_summary = next(r for r in metric['results_summary'] if not r['success'])
        self.assertIn('error_classification', failed_task_summary)
        self.assertEqual(failed_task_summary['error_classification']['type'], "APIError") # From actual classification
        self.assertEqual(failed_task_summary['error_classification']['criticality'], ErrorCriticality.HIGH.value)
        # No mock for classify_error to check calls on


    @patch("src.orchestrator.task_orchestrator.time.strftime")
    def test_run_round_timeout_error_reaction(self, mock_strftime):
        mock_strftime.return_value = "2023-10-26T12:00:00+0000"
        self.orchestrator.add_tasks(["task_timeout"])
        self.orchestrator.batch_size = 1
        initial_timeout_multiplier = self.orchestrator.current_timeout_multiplier

        self.mock_agent.results_to_return = [
            TaskResult(success=False, details="Operation timed out", task_content="task_timeout") # "timed out" is a keyword
        ]
        asyncio.run(self.orchestrator.run_round())
        print(f"DEBUG: Orchestrator timeout multiplier in test after run_round: {self.orchestrator.current_timeout_multiplier}")
        metric = self.orchestrator.metrics_history[0]

        self.assertEqual(self.orchestrator.current_timeout_multiplier, 1.2)

        actions = metric.get('actions_taken', [])
        self.assertTrue(any("Detected TimeoutError" in msg for msg in actions), f"TimeoutError message not found in {actions}")
        self.assertTrue(any("Increased timeout multiplier to 1.20" in msg for msg in actions), f"Timeout multiplier message not found in {actions}")


    @patch("src.orchestrator.task_orchestrator.time.strftime")
    def test_run_round_value_error_reaction(self, mock_strftime):
        mock_strftime.return_value = "2023-10-26T13:00:00+0000"
        self.orchestrator.add_tasks(["task_value_err"])
        self.orchestrator.batch_size = 1

        self.mock_agent.results_to_return = [
            # "valueerror" is a keyword
            TaskResult(success=False, details="ValueError: Received an invalid value for parameter 'X'.", task_content="task_value_err")
        ]
        asyncio.run(self.orchestrator.run_round())

        metric = self.orchestrator.metrics_history[0]
        actions = metric.get('actions_taken', [])
        # print(f"Debug actions_taken for ValueError test: {actions}")
        self.assertTrue(any("Detected ValueError" in msg and "task_value_err" in msg for msg in actions), f"ValueError message not found in {actions}")

    def test_get_status(self):
        self.orchestrator.add_tasks(["t1", "t2", "t3"])
        self.orchestrator.metrics_history = [{"round_data": 1}, {"round_data": 2}]
        status = self.orchestrator.get_status()
        self.assertEqual(status['current_batch_size'], self.orchestrator.batch_size)
        self.assertEqual(status['task_queue_length'], 3)
        self.assertEqual(status['total_metrics_rounds'], 2)
        self.assertEqual(len(status['last_10_rounds_metrics']), 2)

    def test_log_file_corruption_handling(self):
        corrupted_log_content = "this is not json"
        with open(self.log_file, 'w') as f:
            f.write(corrupted_log_content)

        with patch('builtins.print') as mock_print: # Suppress warning print
            new_orchestrator = TaskOrchestrator(agent=self.mock_agent, metrics_log_file=self.log_file)
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, 'r') as f:
            self.assertEqual(json.load(f), [])

        corrupted_json_object = {"corrupted": "data"}
        with open(self.log_file, 'w') as f:
            json.dump(corrupted_json_object, f)

        with patch('builtins.print') as mock_print: # Suppress warning print
            new_orchestrator_2 = TaskOrchestrator(agent=self.mock_agent, metrics_log_file=self.log_file)
        with open(self.log_file, 'r') as f:
            self.assertEqual(json.load(f), [])

    def test_run_round_no_tasks_in_queue(self):
        # No tasks added to orchestrator.task_queue
        initial_metrics_history_len = len(self.orchestrator.metrics_history)
        asyncio.run(self.orchestrator.run_round())
        # Ensure no processing happened, no metrics added
        self.assertEqual(self.mock_agent.call_count, 0)
        self.assertEqual(len(self.orchestrator.metrics_history), initial_metrics_history_len)

    def test_run_round_batch_size_adjustment_multiple_failures(self):
        self.orchestrator.add_tasks(["t1", "t2", "t3"])
        self.orchestrator.batch_size = 3 # Start with a larger batch

        # Ensure details will be classified by the actual error_analyzer
        self.mock_agent.results_to_return = [
            TaskResult(success=True, details="OK", task_content="t1"),
            TaskResult(success=False, details="API error critical failure", task_content="t2"), # "api error"
            TaskResult(success=False, details="Operation has timed out", task_content="t3")    # "timed out"
        ]
        asyncio.run(self.orchestrator.run_round())
        self.assertEqual(self.orchestrator.batch_size, 2) # Reduced from 3 to 2 due to failures

    def test_run_round_max_batch_size_not_exceeded(self):
        self.orchestrator.add_tasks(["t1", "t2"])
        self.orchestrator.batch_size = self.orchestrator.max_batch # Start at max_batch
        self.mock_agent.results_to_return = [
            TaskResult(success=True, details="OK", task_content="t1"),
            TaskResult(success=True, details="OK", task_content="t2")
        ]
        asyncio.run(self.orchestrator.run_round())
        self.assertEqual(self.orchestrator.batch_size, self.orchestrator.max_batch) # Should not exceed max_batch


if __name__ == '__main__':
    unittest.main()
