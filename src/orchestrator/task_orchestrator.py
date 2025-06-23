import time
import json
import os
from typing import List, Any, NamedTuple, Dict
from collections import Counter

# Import for error analysis
from .error_analyzer import classify_error, ErrorCriticality

# Forward declaration for JuliusAgent - This would typically be a concrete class.
class JuliusAgent:
    """
    Abstract representation of an agent capable of processing tasks.

    This class is intended to be subclassed with a concrete implementation
    for actual task processing.
    """
    async def process_tasks(self, tasks: List[str]) -> List['TaskResult']:
        """Processes a list of tasks.

        Args:
            tasks: A list of strings, where each string is a task to be processed.

        Returns:
            A list of TaskResult objects, corresponding to each input task.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError

class TaskResult(NamedTuple):
    """
    Represents the result of a single task processing attempt.

    Attributes:
        success: Boolean indicating if the task was processed successfully.
        details: A string providing details about the outcome (e.g., success message or error string).
        task_content: The original content of the task.
    """
    success: bool
    details: str
    task_content: str

class TaskOrchestrator:
    """
    Manages a queue of tasks, processes them in batches using an agent,
    and adapts its strategy based on task outcomes and error analysis.

    The orchestrator logs metrics for each round of processing, including
    error classifications and adaptive actions taken.
    """
    def __init__(self,
                 agent: JuliusAgent,
                 batch_size: int = 3,
                 max_batch: int = 10,
                 min_batch_size: int = 1,
                 metrics_log_file: str = "orchestrator_log.json"):
        """Initializes the TaskOrchestrator.

        Args:
            agent: An instance of JuliusAgent (or its subclass) to process tasks.
            batch_size: The initial number of tasks to process in a batch.
            max_batch: The maximum allowable batch size.
            min_batch_size: The minimum allowable batch size.
            metrics_log_file: Path to the JSON file for logging metrics.
        """
        self.agent = agent
        self.batch_size = batch_size
        self.min_batch_size = min_batch_size
        self.max_batch = max_batch
        self.task_queue: List[str] = []
        self.metrics_history: List[Dict[str, Any]] = [] # In-memory history of round metrics
        self.metrics_log_file = metrics_log_file
        self._initialize_metrics_log_file()

        # Adaptive parameters
        self.current_timeout_multiplier: float = 1.0
        # self.base_timeout: int = 30 # Example: Could be used if agent's timeout is configurable

    def _initialize_metrics_log_file(self):
        """Ensures the metrics log file exists and is a valid JSON list."""
        if not os.path.exists(self.metrics_log_file):
            with open(self.metrics_log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        else:
            try:
                with open(self.metrics_log_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if not isinstance(content, list):
                        # If content is not a list, file is considered corrupted for our purposes.
                        raise ValueError("Log file content is not a JSON list.")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Metrics log file {self.metrics_log_file} is corrupted ({e}). Initializing as empty list.")
                with open(self.metrics_log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)

    def add_tasks(self, tasks: List[str]) -> None:
        """Adds a list of tasks to the internal processing queue.

        Args:
            tasks: A list of strings, where each string represents a task.
        """
        self.task_queue.extend(tasks)

    def _log_metric_to_file(self, metric_entry: Dict[str, Any]) -> None:
        """Appends a single metric entry to the JSON log file.

        This method reads the existing list of metrics, appends the new entry,
        and writes the entire list back to the file. This is not suitable for
        high-concurrency scenarios without proper file locking.

        Args:
            metric_entry: A dictionary containing the metrics for the current round.
        """
        try:
            log_data: List[Dict[str, Any]] = []
            if os.path.exists(self.metrics_log_file): # Check again, in case it was deleted post-init
                with open(self.metrics_log_file, 'r', encoding='utf-8') as f:
                    try:
                        log_data = json.load(f)
                        if not isinstance(log_data, list):
                            print(f"Warning: Log file {self.metrics_log_file} was corrupted (not a list) before appending. Starting fresh for this entry.")
                            log_data = []
                    except json.JSONDecodeError:
                        print(f"Warning: Log file {self.metrics_log_file} was corrupted (JSON error) before appending. Starting fresh for this entry.")
                        log_data = []

            log_data.append(metric_entry)

            with open(self.metrics_log_file, 'w', encoding='utf-8') as f: # Open in 'w' to overwrite with updated list
                json.dump(log_data, f, indent=4)
        except IOError as e:
            print(f"Error writing to metrics log file {self.metrics_log_file}: {e}")
        except Exception as e:
            print(f"Unexpected error during metrics logging: {e}")

    async def run_round(self) -> None:
        """
        Executes one round of task processing.

        It takes a batch of tasks from the queue, sends them to the agent,
        collects results, classifies errors, logs metrics, and adjusts
        adaptive parameters (like batch size and timeout multiplier)
        based on the outcomes.
        """
        if not self.task_queue:
            print("Task queue is empty. No round to run.")
            return

        actual_batch_size = min(self.batch_size, len(self.task_queue))
        if actual_batch_size == 0: # Should not happen if task_queue is not empty, but as a safeguard.
            print("No tasks to process in this batch (actual_batch_size is 0).")
            return

        batch_tasks = [self.task_queue.pop(0) for _ in range(actual_batch_size)]

        start_time = time.time()
        try:
            results: List[TaskResult] = await self.agent.process_tasks(batch_tasks)
        except Exception as agent_exception:
            # Handle exceptions raised by the agent's process_tasks method itself
            print(f"Agent's process_tasks failed with exception: {agent_exception}")
            # Treat all tasks in this batch as failed due to agent error
            elapsed_time = time.time() - start_time
            failed_tasks_count = len(batch_tasks)
            error_classification = classify_error(str(agent_exception)) # Classify the agent's exception

            processed_results_summary = [{
                'task': task_content,
                'success': False,
                'details': f"Agent processing error: {str(agent_exception)}",
                'error_classification': classify_error(f"Agent processing error: {str(agent_exception)}")
            } for task_content in batch_tasks]

            error_criticality_counts = Counter()
            for res_summary in processed_results_summary:
                 if 'error_classification' in res_summary:
                    error_criticality_counts[res_summary['error_classification']['criticality']] += 1

            round_metric = {
                'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                'batch_size_at_round_start': self.batch_size,
                'tasks_processed_count': len(batch_tasks),
                'successful_tasks_count': 0,
                'failed_tasks_count': failed_tasks_count,
                'success_rate': 0.0,
                'time_taken_seconds': round(elapsed_time, 2),
                'error_summary_by_criticality': dict(error_criticality_counts),
                'batch_tasks_content': batch_tasks,
                'results_summary': processed_results_summary,
                'actions_taken': [f"Agent failed to process batch. Error: {error_classification['type']} ({error_classification['description']})"]
            }
            self.metrics_history.append(round_metric)
            self._log_metric_to_file(round_metric)
            # Drastically reduce batch size on agent failure
            self.batch_size = self.min_batch_size
            print(f"Round completed with agent error. Batch size reduced to {self.batch_size}. Error: {agent_exception}")
            return

        elapsed_time = time.time() - start_time
        successful_tasks_count = 0
        failed_tasks_count = 0
        processed_results_summary = []
        error_criticality_counts = Counter()

        for r in results:
            if r.success:
                successful_tasks_count += 1
                processed_results_summary.append({
                    'task': r.task_content,
                    'success': r.success,
                    'details': r.details
                })
            else:
                failed_tasks_count += 1
                error_classification = classify_error(r.details)
                processed_results_summary.append({
                    'task': r.task_content,
                    'success': r.success,
                    'details': r.details,
                    'error_classification': error_classification
                })
                error_criticality_counts[error_classification['criticality']] += 1

        success_rate = (successful_tasks_count / len(results)) if results else 0.0

        round_metric = {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            'batch_size_at_round_start': self.batch_size,
            'tasks_processed_count': len(batch_tasks),
            'successful_tasks_count': successful_tasks_count,
            'failed_tasks_count': failed_tasks_count,
            'success_rate': round(success_rate, 2),
            'time_taken_seconds': round(elapsed_time, 2),
            'error_summary_by_criticality': dict(error_criticality_counts), # Log aggregated error stats
            'batch_tasks_content': batch_tasks,
            'results_summary': processed_results_summary # Now includes error_classification
        }

        self.metrics_history.append(round_metric)
        self._log_metric_to_file(round_metric)

        # --- Automatic Error Handling Reactions & Adjustments ---
        action_taken_messages = []

        # 1. Adjust batch_size based on overall round performance
        if successful_tasks_count == len(results) and len(results) > 0:
            self.batch_size = min(self.batch_size + 1, self.max_batch)
            self.current_timeout_multiplier = max(1.0, self.current_timeout_multiplier - 0.1) # Gradually reduce timeout multiplier
            action_taken_messages.append(f"Increased batch size to {self.batch_size}. Reduced timeout multiplier to {self.current_timeout_multiplier:.2f}.")
        elif failed_tasks_count > 0:
            self.batch_size = max(self.min_batch_size, self.batch_size - 1)
            action_taken_messages.append(f"Decreased batch size to {self.batch_size} due to failures.")

        # 2. React to specific error types from this round for future rounds
        # (Note: Retries for API errors are complex and better handled by making the agent itself more robust or having a separate retry queue.
        # For now, we'll log the intent and adjust parameters like timeout.)

        high_criticality_timeout_errors = 0
        high_criticality_api_errors = 0

        for res_summary in processed_results_summary:
            if not res_summary['success'] and 'error_classification' in res_summary:
                classification = res_summary['error_classification']

                # TimeoutError Handling
                if classification['type'] == "TimeoutError":
                    self.current_timeout_multiplier = min(2.0, self.current_timeout_multiplier + 0.2) # Increase timeout multiplier more aggressively
                    action_taken_messages.append(f"Detected TimeoutError. Increased timeout multiplier to {self.current_timeout_multiplier:.2f}.")
                    if classification['criticality'] == ErrorCriticality.HIGH.value:
                         high_criticality_timeout_errors +=1

                # APIError: Log intent for retry with backoff (actual retry is out of scope for this step)
                elif classification['type'] == "APIError":
                    action_taken_messages.append(f"Detected APIError for task '{res_summary['task']}'. Recommended: Retry with exponential backoff.")
                    if classification['criticality'] == ErrorCriticality.HIGH.value:
                        high_criticality_api_errors +=1

                # TypeError or ValueError: Log recommendation for input validation
                elif classification['type'] in ["TypeError", "ValueError"]:
                    action_taken_messages.append(f"Detected {classification['type']} for task '{res_summary['task']}'. Recommended: Validate inputs before task execution.")

        # Log actions taken for observability
        if action_taken_messages:
            round_metric['actions_taken'] = action_taken_messages
            # Re-log if you want 'actions_taken' persisted; for now, just print
            print(f"Actions taken this round: {'; '.join(action_taken_messages)}")

        # Example: If a high proportion of tasks in the batch result in critical Timeout or API errors,
        # take a more drastic measure like reducing batch size to minimum.
        # This helps to quickly stabilize if the system is overwhelmed or an external API is consistently failing.
        if actual_batch_size > 0 and \
           (high_criticality_timeout_errors > actual_batch_size / 2 or \
            high_criticality_api_errors > actual_batch_size / 2):
            self.batch_size = self.min_batch_size
            warning_message = f"WARNING: High proportion of critical Timeout/API errors. Batch size drastically reduced to {self.batch_size}."
            action_taken_messages.append(warning_message) # Also log this drastic action
            print(warning_message)

        # Update round_metric with actions_taken if they were recorded and not already part of a premature exit (like agent failure)
        if 'actions_taken' not in round_metric and action_taken_messages : # Check if actions_taken is already set
             round_metric['actions_taken'] = action_taken_messages


        print(f"Round completed. New Batch_size: {self.batch_size}. Processed: {len(batch_tasks)}. Success: {successful_tasks_count}. Failed: {failed_tasks_count}. Time: {elapsed_time:.2f}s. Success Rate: {success_rate:.0%}. Errors by criticality: {dict(error_criticality_counts)}. Current Timeout Multiplier: {self.current_timeout_multiplier:.2f}")

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieves the current operational status of the orchestrator.

        Returns:
            A dictionary containing:
                - 'current_batch_size' (int): The current adaptive batch size.
                - 'task_queue_length' (int): Number of tasks pending in the queue.
                - 'total_metrics_rounds' (int): Total number of rounds processed and logged in memory.
                - 'last_10_rounds_metrics' (List[Dict]): Metrics from the last 10 (or fewer) rounds.
        """
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": len(self.task_queue),
            "total_metrics_rounds": len(self.metrics_history), # Based on in-memory history
            "last_10_rounds_metrics": self.metrics_history[-10:] # Slice of in-memory history
        }

# Example Usage (Illustrative)
async def example_run():
    class MockSuccessfulAgent(JuliusAgent):
        async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
            print(f"MockAgent processing: {tasks}")
            return [TaskResult(True, "Successfully processed", task) for task in tasks]

    class MockErrorAgent(JuliusAgent):
        _call_count = 0
        async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
            MockErrorAgent._call_count += 1
            results = []
            for i, task in enumerate(tasks):
                if MockErrorAgent._call_count % 4 == 1 and i == 0 : # First task of every 4th call fails with API error
                     results.append(TaskResult(False, "API Error: Service unavailable (simulated)", task))
                elif MockErrorAgent._call_count % 4 == 2 and i == 0: # First task of every other 4th call fails with Timeout
                    results.append(TaskResult(False, "Operation timed out (simulated)", task))
                elif MockErrorAgent._call_count % 4 == 3 and i ==0: # Value Error
                     results.append(TaskResult(False, "ValueError: Invalid parameter (simulated)", task))
                else:
                    results.append(TaskResult(True, "Successfully processed", task))
            print(f"MockErrorAgent processing (call {MockErrorAgent._call_count}): {tasks} -> {[(r.success, r.details) for r in results]}")
            await asyncio.sleep(0.1) # Simulate some processing time
            return results

    # orchestrator = TaskOrchestrator(agent=MockSuccessfulAgent(), batch_size=2, metrics_log_file="example_orchestrator_log_success.json")
    orchestrator = TaskOrchestrator(agent=MockErrorAgent(), batch_size=2, min_batch_size=1, max_batch=4, metrics_log_file="example_orchestrator_log_errors.json")

    tasks_to_add = [f"Task {i+1}" for i in range(20)]
    orchestrator.add_tasks(tasks_to_add)

    print(f"Initial status: {orchestrator.get_status()}")

    round_num = 0
    while len(orchestrator.task_queue) > 0:
        round_num+=1
        print(f"\n--- Running Round {round_num} ---")
        await orchestrator.run_round()
        print(f"Status after round {round_num}: {orchestrator.get_status()['current_batch_size']=}, {orchestrator.get_status()['task_queue_length']=}")
        # await asyncio.sleep(0.5) # Simulate delay between rounds if needed

    print("\n--- All tasks processed ---")
    print(f"Final status: {orchestrator.get_status()}")
    # print(f"Full metrics history: {json.dumps(orchestrator.metrics_history, indent=2)}")


if __name__ == "__main__":
    # To clear previous example logs if they exist
    for log_f in ["example_orchestrator_log_success.json", "example_orchestrator_log_errors.json"]:
        if os.path.exists(log_f):
            os.remove(log_f)

    asyncio.run(example_run())
