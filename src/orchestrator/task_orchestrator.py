import time
import json
import os
from typing import List, Any, NamedTuple, Dict

# Forward declaration for JuliusAgent
# Assuming src is in PYTHONPATH for these imports
from src.connectors import core_connector
from src.telemetry.command_telemetry import log_command_event, configure_telemetry_logging as configure_task_telemetry
from src.agents.n8n_agent import N8nAgent

# Configure telemetry for the orchestrator module if not already done by bot
# This ensures telemetry is active if orchestrator is used standalone.
# It's designed to be safe to call multiple times.
try:
    if configure_task_telemetry:
        configure_task_telemetry(enable_console_logging=False) # Default file, no extra console logs
except NameError: # Should not happen if imports work
    print("Warning: configure_task_telemetry not available in task_orchestrator.")
except Exception as e:
    print(f"Error configuring telemetry in task_orchestrator: {e}")


class JuliusAgent:
    async def process_tasks(self, tasks: List[Dict[str, Any]]) -> List['TaskResult']: # Changed to List[Dict]
        raise NotImplementedError

class TaskResult(NamedTuple):
    success: bool
    details: str
    task_content: Dict[str, Any] # Changed to Dict

class KatanaTaskProcessor(JuliusAgent):
    """
    Concrete implementation of JuliusAgent for processing Katana tasks.
    """
    def __init__(self):
        # Potentially initialize connections or configurations here
        pass

    async def process_tasks(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
        results: List[TaskResult] = []
        for task_data in tasks:
            task_id = task_data.get("id", f"task_{time.time_ns()}") # Ensure a task_id
            task_type = task_data.get("type", "unknown_task_type")

            log_command_event(
                event_type=f"katana_task_{task_type}_started",
                command_id=task_id,
                details={"task_data": task_data}
            )

            try:
                # Simulate processing based on task type
                # For example, a task might involve calling the core_connector
                if task_type == "example_core_call":
                    core_success, core_details = core_connector.call_sc_core(task_data)
                    if core_success:
                        results.append(TaskResult(True, f"Core call successful: {core_details.get('result', '')}", task_data))
                        log_command_event(event_type=f"katana_task_{task_type}_completed", command_id=task_id, details=core_details, success=True)
                    else:
                        results.append(TaskResult(False, f"Core call failed: {core_details.get('error', '')}", task_data))
                        log_command_event(event_type=f"katana_task_{task_type}_failed", command_id=task_id, details=core_details, success=False)

                elif task_type == "n8n_workflow_generation":
                    try:
                        agent = N8nAgent()
                        task_description = task_data.get("description", "No description provided.")
                        workflow_json = agent.create_workflow(task_description)
                        # For now, the result detail will be the JSON itself
                        results.append(TaskResult(True, workflow_json, task_data))
                        log_command_event(event_type=f"katana_task_{task_type}_completed", command_id=task_id, details={"workflow_name": "E-commerce Order Processing"}, success=True)
                    except Exception as agent_e:
                        error_msg = f"N8nAgent failed: {agent_e}"
                        results.append(TaskResult(False, error_msg, task_data))
                        log_command_event(event_type=f"katana_task_{task_type}_failed", command_id=task_id, details={"error": str(agent_e)}, success=False)

                elif task_type == "text_generation": # From dao_task_handler mock
                    # This would be where an NLP model is invoked for the task if not handled by Telegram bot directly
                    # For now, just acknowledge and mock success
                    time.sleep(0.05) # Simulate work
                    results.append(TaskResult(True, "Text generation task acknowledged (mocked).", task_data))
                    log_command_event(event_type=f"katana_task_{task_type}_completed", command_id=task_id, details={"info": "mocked completion"}, success=True)

                elif task_type == "log_event": # From dao_task_handler mock, if it becomes an orchestrator task
                    # The event might have already been logged if it came via Telegram command.
                    # If it's a direct task, log it here.
                    log_details = task_data.get("args", {})
                    log_details["origin"] = "orchestrator_task"
                    log_command_event(
                        event_type=log_details.get("event_name", "orchestrator_custom_log"),
                        command_id=task_id,
                        details=log_details,
                        success=True
                    )
                    results.append(TaskResult(True, "Log event task processed by orchestrator.", task_data))

                else:
                    # Generic handler for other task types
                    print(f"[KatanaTaskProcessor] Received generic task type '{task_type}' for ID '{task_id}'. Simulating success.")
                    time.sleep(0.02) # Simulate light work
                    results.append(TaskResult(True, f"Generic task '{task_type}' processed (mocked).", task_data))
                    log_command_event(event_type=f"katana_task_{task_type}_completed", command_id=task_id, details={"info": "mocked generic completion"}, success=True)

            except Exception as e:
                error_msg = f"Error processing task {task_id} of type {task_type}: {e}"
                print(f"[KatanaTaskProcessor] {error_msg}")
                results.append(TaskResult(False, error_msg, task_data))
                log_command_event(event_type=f"katana_task_{task_type}_exception", command_id=task_id, details={"error": str(e)}, success=False)

        return results


class TaskOrchestrator:
    def __init__(self, agent: JuliusAgent, batch_size: int = 3, max_batch: int = 10, metrics_log_file: str = "orchestrator_log.json"):
        self.agent = agent
        self.batch_size = batch_size
        self.min_batch_size = 1
        self.max_batch = max_batch
        self.task_queue: List[Dict[str, Any]] = [] # Changed to List[Dict]
        self.metrics_history: List[Dict[str, Any]] = []
        self.metrics_log_file = metrics_log_file
        self._initialize_metrics_log_file()

    def _initialize_metrics_log_file(self):
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


    def add_tasks(self, tasks: List[Dict[str, Any]]) -> None:
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

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус и историю последних 10 раундов из памяти."""
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": len(self.task_queue),
            "total_metrics_rounds": len(self.metrics_history),
            "last_10_rounds_metrics": self.metrics_history[-10:]
        }
