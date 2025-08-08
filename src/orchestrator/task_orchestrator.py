import time
import json
import os
import redis
from typing import List, Any, NamedTuple, Dict

# Forward declaration for JuliusAgent
class JuliusAgent:
    async def process_tasks(self, tasks: List[str]) -> List['TaskResult']:
        raise NotImplementedError

class TaskResult(NamedTuple):
    success: bool
    details: str
    task_content: str

class TaskOrchestrator:
    def __init__(self,
                 agent: JuliusAgent,
                 redis_host: str,
                 redis_port: int,
                 redis_db: int,
                 redis_password: str = None,
                 task_queue_name: str = "katana:task_queue",
                 batch_size: int = 3,
                 max_batch: int = 10,
                 metrics_log_file: str = "orchestrator_log.json"):
        self.agent = agent
        self.batch_size = batch_size
        self.min_batch_size = 1
        self.max_batch = max_batch
        self.metrics_history: List[Dict[str, Any]] = []
        self.metrics_log_file = metrics_log_file
        self.task_queue_name = task_queue_name

        print(f"Connecting to Redis at {redis_host}:{redis_port}...")
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False # We'll decode manually after popping
            )
            # Check connection
            self.redis_client.ping()
            print("✅ Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            print(f"❌ Failed to connect to Redis: {e}")
            raise

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
        """Взять batch_size задач из Redis, отправить Julius и собрать результат."""
        current_queue_size = self.redis_client.llen(self.task_queue_name)
        if current_queue_size == 0:
            # This is expected when idle, so no print statement is needed.
            return

        actual_batch_size = min(self.batch_size, current_queue_size)

        # Use a pipeline to atomically get a batch of tasks and trim the list.
        # This is an efficient way to dequeue multiple items.
        pipe = self.redis_client.pipeline()
        pipe.lrange(self.task_queue_name, 0, actual_batch_size - 1)
        pipe.ltrim(self.task_queue_name, actual_batch_size, -1)
        # The result of the lrange command is the first item in the pipeline's result
        batch_tasks_bytes = pipe.execute()[0]

        batch_tasks = [task.decode('utf-8') for task in batch_tasks_bytes]

        if not batch_tasks:
            # This can happen in a race condition if another process clears the queue
            # between the llen check and the pipeline execution.
            print("No tasks to process in this batch (race condition).")
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

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус и историю последних 10 раундов из памяти."""
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": self.redis_client.llen(self.task_queue_name),
            "total_metrics_rounds": len(self.metrics_history),
            "last_10_rounds_metrics": self.metrics_history[-10:]
        }
