import time
import json
import os
from typing import List, Any, NamedTuple, Dict
from src.memory.memory import Memory
from src.agents.sync_agent import SyncAgent

# Forward declaration for JuliusAgent
class JuliusAgent:
    async def process_tasks(self, tasks: List[str]) -> List['TaskResult']:
        raise NotImplementedError

class TaskResult(NamedTuple):
    success: bool
    details: str
    task_content: str

class TaskOrchestrator:
    def __init__(self, agent: JuliusAgent, memory: Memory, sync_agent: SyncAgent, batch_size: int = 3, max_batch: int = 10, metrics_log_file: str = "orchestrator_log.json"):
        self.agent = agent
        self.memory = memory
        self.sync_agent = sync_agent
        self.batch_size = batch_size
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
        for task in tasks:
            self.task_queue.append(task)
            self.memory.add_task(task)

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
        batch_tasks = [self.task_queue.pop(0) for _ in range(actual_batch_size)]

        if not batch_tasks:
            print("No tasks to process in this batch.")
            return

        start_time = time.time()
        results: List[TaskResult] = await self.agent.process_tasks(batch_tasks)
        elapsed_time = time.time() - start_time

        successful_tasks_count = sum(1 for r in results if r.success)
        failed_tasks_count = len(results) - successful_tasks_count
        success_rate = (successful_tasks_count / len(results)) if results else 0.0

        round_metric = {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            'batch_size_at_round_start': self.batch_size,
            'tasks_processed_count': len(batch_tasks),
            'successful_tasks_count': successful_tasks_count,
            'failed_tasks_count': failed_tasks_count,
            'success_rate': round(success_rate, 2),
            'time_taken_seconds': round(elapsed_time, 2),
            'batch_tasks_content': batch_tasks,
            'results_summary': [{'task': r.task_content, 'success': r.success, 'details': r.details} for r in results]
        }

        self.metrics_history.append(round_metric)
        self._log_metric_to_file(round_metric) # Log this round's metric to file

        # Adjust batch_size based on results
        if successful_tasks_count == len(results) and len(results) > 0:
            self.batch_size = min(self.batch_size + 1, self.max_batch)
        elif failed_tasks_count > 1:
            self.batch_size = max(self.min_batch_size, self.batch_size - 1)

        print(f"Round completed. New Batch_size: {self.batch_size}. Processed: {len(batch_tasks)}. Success: {successful_tasks_count}. Failed: {failed_tasks_count}. Time: {elapsed_time:.2f}s. Success Rate: {success_rate:.0%}")

        # Sync memories
        self.sync_agent.sync_memories(self.memory.memory_dir)

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус и историю последних 10 раундов из памяти."""
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": len(self.task_queue),
            "total_metrics_rounds": len(self.metrics_history),
            "last_10_rounds_metrics": self.metrics_history[-10:]
        }
