import time
import json
import os
from typing import List, Any, NamedTuple, Dict

# Forward declaration for JuliusAgent
# Ensure this import points to the updated JuliusAgent that may wrap KatanaAgent
from src.agents.julius_agent import JuliusAgent

class TaskResult(NamedTuple):
    success: bool
    details: str
    task_content: str # This refers to the original task string

class Task(NamedTuple):
    content: str
    retries: int
    priority: int # Lower number means higher priority

class TaskOrchestrator:
    DEFAULT_PRIORITY = 10
    RETRY_PRIORITY = 1 # Higher priority for retries
    MAX_RETRIES = 3

    def __init__(self, agent: JuliusAgent, batch_size: int = 3, max_batch: int = 10, metrics_log_file: str = "orchestrator_log.json"):
        self.agent = agent
        self.batch_size = batch_size
        self.min_batch_size = 1
        self.max_batch = max_batch
        self.task_queue: List[Task] = [] # Changed to List[Task]
        self.metrics_history: List[Dict[str, Any]] = []
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
        for task_content in tasks:
            self.task_queue.append(Task(content=task_content, retries=0, priority=self.DEFAULT_PRIORITY))
        # Sort queue by priority (lower number first) and then by retries (lower number first)
        self.task_queue.sort(key=lambda t: (t.priority, t.retries))


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

        # Sort queue by priority (lower number first) and then by retries (lower number first)
        # This ensures high priority/retried tasks are at the front.
        self.task_queue.sort(key=lambda t: (t.priority, t.retries))

        actual_batch_size = min(self.batch_size, len(self.task_queue))
        current_batch_tasks_objects: List[Task] = [self.task_queue.pop(0) for _ in range(actual_batch_size)]

        if not current_batch_tasks_objects:
            print("No tasks to process in this batch.")
            return

        # Extract content for the agent
        batch_tasks_content = [task.content for task in current_batch_tasks_objects]

        start_time = time.time()
        results: List[TaskResult] = await self.agent.process_tasks(batch_tasks_content)
        elapsed_time = time.time() - start_time

        successful_tasks_count = 0
        failed_tasks_count = 0
        error_types_summary = {}
        processed_task_details_for_log = []


        # Process results and handle retries
        for task_obj, result in zip(current_batch_tasks_objects, results):
            processed_task_details_for_log.append({
                'task_content': result.task_content, # original content from TaskResult
                'success': result.success,
                'details': result.details,
                'retries_attempted': task_obj.retries
            })
            if result.success:
                successful_tasks_count += 1
            else:
                failed_tasks_count += 1
                # Basic error categorization
                error_type = "GENERAL_FAILURE"
                if "timeout" in result.details.lower(): error_type = "TIMEOUT_ERROR"
                elif "connection" in result.details.lower(): error_type = "CONNECTION_ERROR"
                error_types_summary[error_type] = error_types_summary.get(error_type, 0) + 1

                # Retry logic
                if task_obj.retries < self.MAX_RETRIES:
                    new_retries = task_obj.retries + 1
                    # Re-add to queue with increased retry count and higher priority
                    self.task_queue.append(Task(content=task_obj.content, retries=new_retries, priority=self.RETRY_PRIORITY))
                    print(f"Task '{task_obj.content}' failed, will retry (attempt {new_retries}/{self.MAX_RETRIES}).")
                else:
                    print(f"Task '{task_obj.content}' failed after {self.MAX_RETRIES} retries. Giving up.")

        # Re-sort queue after adding retried tasks
        self.task_queue.sort(key=lambda t: (t.priority, t.retries))

        success_rate = (successful_tasks_count / len(current_batch_tasks_objects)) if current_batch_tasks_objects else 0.0
        time_per_task = (elapsed_time / len(current_batch_tasks_objects)) if current_batch_tasks_objects else 0.0

        round_metric = {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            'batch_size_at_round_start': self.batch_size,
            'tasks_processed_in_batch': len(current_batch_tasks_objects),
            'successful_tasks_count': successful_tasks_count,
            'failed_tasks_count': failed_tasks_count, # In this batch, not overall
            'success_rate_in_batch': round(success_rate, 2),
            'time_taken_seconds': round(elapsed_time, 2),
            'avg_time_per_task_seconds': round(time_per_task, 3),
            'error_types_in_batch': error_types_summary,
            # 'batch_tasks_content_with_retry_info': [{'content': t.content, 'retries': t.retries, 'priority': t.priority} for t in current_batch_tasks_objects],
            'results_summary': processed_task_details_for_log # Updated to include retry info
        }

        self.metrics_history.append(round_metric)
        self._log_metric_to_file(round_metric)

        # Adjust batch_size based on results of this batch
        if successful_tasks_count == len(current_batch_tasks_objects) and len(current_batch_tasks_objects) > 0:
            self.batch_size = min(self.batch_size + 1, self.max_batch)
        elif failed_tasks_count > 0 : # Be more conservative: if any task failed, consider reducing batch size or keeping it.
            self.batch_size = max(self.min_batch_size, self.batch_size -1 if failed_tasks_count > 1 else self.batch_size)


        print(f"Round completed. New Batch_size: {self.batch_size}. Processed in batch: {len(current_batch_tasks_objects)}. Success: {successful_tasks_count}. Failed: {failed_tasks_count}. Retries pending: {sum(1 for t in self.task_queue if t.priority == self.RETRY_PRIORITY)}. Total queue: {len(self.task_queue)}. Time: {elapsed_time:.2f}s. Success Rate (batch): {success_rate:.0%}")

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус и историю последних 10 раундов из памяти."""
        # Provide more details about the task queue in status
        task_queue_summary = [
            {'content': task.content, 'retries': task.retries, 'priority': task.priority}
            for task in self.task_queue[:20] # Show first 20 tasks to keep it manageable
        ]
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": len(self.task_queue),
            "task_queue_preview": task_queue_summary, # Added
            "tasks_pending_retry": sum(1 for t in self.task_queue if t.priority == self.RETRY_PRIORITY and t.retries > 0), # Added
            "max_retries_per_task": self.MAX_RETRIES, # Added
            "total_metrics_rounds": len(self.metrics_history),
            "last_10_rounds_metrics": self.metrics_history[-10:]
        }
