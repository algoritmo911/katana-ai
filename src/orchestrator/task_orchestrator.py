import time
import json
import os
import time
import json
import os
import asyncio # Required for asyncio.to_thread
from typing import List, Any, NamedTuple, Dict
from src.agents.katana_agent import KatanaAgent # Import KatanaAgent
from bot.nlp_clients.base_nlp_client import NLPServiceError # For catching specific errors

# TaskResult remains the same, as KatanaAgent's output will be adapted to it.
class TaskResult(NamedTuple):
    success: bool
    details: str # For KatanaAgent, this will be the LLM response or error message
    task_content: str

class TaskOrchestrator:
    def __init__(self, agent: KatanaAgent, batch_size: int = 3, max_batch: int = 10, metrics_log_file: str = "orchestrator_log.json"):
        self.agent = agent
        self.batch_size = batch_size
        # Ensure min_batch_size is defined, it was missing in the original snippet for KatanaAgent context
        self.min_batch_size = 1
        self.max_batch = max_batch
        self.task_queue: List[str] = []
        self.metrics_history: List[Dict[str, Any]] = [] # Renamed from self.metrics to avoid confusion with a single metric entry
        self.metrics_log_file = metrics_log_file
        self._initialize_metrics_log_file()

    def _initialize_metrics_log_file(self):
        # Create an empty JSON array in the log file if it doesn't exist or is invalid
        if not os.path.exists(self.metrics_log_file):
            with open(self.metrics_log_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
        else:
            try:
                with open(self.metrics_log_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if not isinstance(content, list):
                        raise ValueError("Log file is not a JSON list")
            except (json.JSONDecodeError, ValueError):
                print(f"Warning: Metrics log file {self.metrics_log_file} is corrupted. Initializing as empty list.")
                with open(self.metrics_log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)


    def add_tasks(self, tasks: List[str]) -> None:
        """Добавить список задач в очередь."""
        self.task_queue.extend(tasks)

    def _log_metric_to_file(self, metric_entry: Dict[str, Any]):
        """Appends a single metric entry to the JSON log file."""
        try:
            # Read existing entries
            with open(self.metrics_log_file, 'r+', encoding='utf-8') as f:
                # Lock the file if possible (platform dependent, not strictly enforced here for simplicity)
                # For robust concurrent access, a proper file locking mechanism or a database would be better.
                try:
                    log_data = json.load(f)
                except json.JSONDecodeError:
                    log_data = [] # If file is empty or corrupted, start fresh for this entry

                if not isinstance(log_data, list): # Ensure it's a list
                    log_data = []

                log_data.append(metric_entry)
                f.seek(0) # Go to the beginning of the file
                json.dump(log_data, f, indent=4) # Write back with indent for readability
                f.truncate() # Remove any trailing old content if new content is shorter
        except IOError as e:
            print(f"Error writing to metrics log file {self.metrics_log_file}: {e}")
        except Exception as e: # Catch any other unexpected errors during logging
            print(f"Unexpected error during metrics logging: {e}")


    async def run_round(self) -> None:
        """Взять batch_size задач, отправить Julius и собрать результат."""
        if not self.task_queue:
            print("Task queue is empty. No round to run.")
            return

        actual_batch_size = min(self.batch_size, len(self.task_queue))
        current_batch_tasks = [self.task_queue.pop(0) for _ in range(actual_batch_size)]

        if not current_batch_tasks:
            print("No tasks to process in this batch.")
            return

        start_time = time.time()
        results: List[TaskResult] = []

        # KatanaAgent.handle_task is synchronous but potentially I/O bound (network calls).
        # To avoid blocking the asyncio event loop, run these synchronous calls in a thread pool.
        # We process them "concurrently" from the event loop's perspective, but each call
        # to handle_task will run sequentially within its own thread if the executor has limited workers.
        # The overall batch processing here remains effectively sequential in terms of waiting for all results,
        # but individual calls don't block the main loop.

        # If true parallelism of NLP calls within a batch is desired AND KatanaAgent/LLM clients
        # support async operations, KatanaAgent.handle_task should be made async,
        # and asyncio.gather could be used here.

        task_coroutines = []
        for task_content in current_batch_tasks:
            # Wrap the synchronous call self.agent.handle_task in asyncio.to_thread
            # Each call will return a TaskResult or raise an exception.
            # We need a helper to run and package the result/exception.
            async def process_single_task_in_thread(content):
                try:
                    response = await asyncio.to_thread(self.agent.handle_task, task_prompt=content)
                    return TaskResult(success=True, details=response, task_content=content)
                except NLPServiceError as e:
                    print(f"Task failed due to NLPServiceError: {e.user_message} (Task: {content})")
                    return TaskResult(success=False, details=e.user_message, task_content=content)
                except Exception as e:
                    error_message = f"Unexpected error processing task: {str(e)} (Task: {content})"
                    print(error_message)
                    return TaskResult(success=False, details=error_message, task_content=content)

            task_coroutines.append(process_single_task_in_thread(task_content))

        # Execute all tasks in the batch "concurrently" from event loop's view
        results = await asyncio.gather(*task_coroutines)

        elapsed_time = time.time() - start_time

        successful_tasks_count = sum(1 for r in results if r.success)
        failed_tasks_count = len(results) - successful_tasks_count
        success_rate = (successful_tasks_count / len(results)) if results else 0.0

        round_metric = {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            'batch_size_at_round_start': self.batch_size, # This is the batch size *before* potential adjustment
            'tasks_processed_count': len(current_batch_tasks),
            'successful_tasks_count': successful_tasks_count,
            'failed_tasks_count': failed_tasks_count,
            'success_rate': round(success_rate, 2),
            'time_taken_seconds': round(elapsed_time, 2),
            'batch_tasks_content': current_batch_tasks, # Log the tasks that were part of this batch
            'results_summary': [{'task': r.task_content, 'success': r.success, 'details': r.details} for r in results]
        }

        self.metrics_history.append(round_metric)
        self._log_metric_to_file(round_metric)

        # Adjust batch_size based on results
        # This logic can remain the same.
        if successful_tasks_count == len(results) and len(results) > 0: # All tasks in batch succeeded
            self.batch_size = min(self.batch_size + 1, self.max_batch)
        elif failed_tasks_count > 0: # Any failure, or if more than 1 as per original logic
            # Original logic: failed_tasks_count > 1. Let's stick to that unless specified otherwise.
            # If even one failure should decrease batch size, change to: elif failed_tasks_count > 0:
             if failed_tasks_count > 1: # Sticking to original condition
                self.batch_size = max(self.min_batch_size, self.batch_size - 1)

        print(f"Round completed. New Batch_size: {self.batch_size}. Processed: {len(current_batch_tasks)}. Success: {successful_tasks_count}. Failed: {failed_tasks_count}. Time: {elapsed_time:.2f}s. Success Rate: {success_rate:.0%}")

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус и историю последних 10 раундов из памяти (или всех, если меньше 10)."""
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": len(self.task_queue),
            "total_metrics_rounds": len(self.metrics_history),
            "last_10_rounds_metrics": self.metrics_history[-10:]
        }
