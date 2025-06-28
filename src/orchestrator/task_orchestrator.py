import time
import json
import os
import logging # Added for logging
from typing import List, Any, NamedTuple, Dict, Optional # Added Optional

# Attempt to import SelfEvolver, handling potential ImportError
try:
    from katana.self_evolve import SelfEvolver
except ImportError:
    print("WARNING: katana.self_evolve.SelfEvolver could not be imported. Auto-patching will be disabled.")
    SelfEvolver = None

logger = logging.getLogger(__name__) # Added logger

# Forward declaration for JuliusAgent
class JuliusAgent:
    async def process_tasks(self, tasks: List[str]) -> List['TaskResult']:
        raise NotImplementedError

class TaskResult(NamedTuple):
    success: bool
    details: str # This can be a simple string or a JSON string with more structured info
    task_content: str
    # New fields for auto-patching information
    patched_attempted: bool = False
    patch_suggested_content: Optional[str] = None
    patch_applied_successfully: Optional[bool] = None
    success_after_patch: Optional[bool] = None
    details_after_patch: Optional[str] = None


class TaskOrchestrator:
    def __init__(self, agent: JuliusAgent, batch_size: int = 3, max_batch: int = 10, metrics_log_file: str = "orchestrator_log.json"):
        self.agent = agent
        self.batch_size = batch_size
        self.min_batch_size = 1
        self.max_batch = max_batch
        self.task_queue: List[str] = []
        self.metrics_history: List[Dict[str, Any]] = []
        self.metrics_log_file = metrics_log_file

        if SelfEvolver:
            self.self_evolver = SelfEvolver()
            logger.info("SelfEvolver initialized for auto-patching.")
        else:
            self.self_evolver = None
            logger.warning("SelfEvolver not available. Auto-patching will be disabled.")

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
        batch_tasks = [self.task_queue.pop(0) for _ in range(actual_batch_size)]

        if not batch_tasks:
            print("No tasks to process in this batch.")
            return

        start_time = time.time()
        initial_results: List[TaskResult] = await self.agent.process_tasks(batch_tasks)
        elapsed_time = time.time() - start_time # Initial processing time

        processed_results: List[TaskResult] = []

        for i, initial_res in enumerate(initial_results):
            task_content = batch_tasks[i] # Assuming initial_results matches order of batch_tasks
            current_res = initial_res

            if not current_res.success and self.self_evolver:
                logger.info(f"Task '{task_content}' failed. Attempting auto-patching. Error: {current_res.details}")
                patch_suggested_content = self.self_evolver.generate_patch(current_res.details)

                if patch_suggested_content:
                    logger.info(f"Patch suggested for task '{task_content}':\n{patch_suggested_content}")
                    patch_applied_successfully = self.self_evolver.apply_patch(patch_suggested_content)
                    logger.info(f"Patch application for task '{task_content}' was: {'successful' if patch_applied_successfully else 'failed'}")

                    if patch_applied_successfully:
                        # Re-verify the task
                        logger.info(f"Re-verifying task '{task_content}' after patch application.")
                        # This is a critical part: re-processing a single task.
                        # We expect process_tasks to return a list, so we take the first element.
                        # Ensure agent.process_tasks can handle a single task list and returns TaskResult objects.
                        retry_results: List[TaskResult] = await self.agent.process_tasks([task_content])
                        if retry_results:
                            retry_res = retry_results[0]
                            processed_results.append(TaskResult(
                                success=retry_res.success, # Final success is success after patch
                                details=current_res.details, # Original error details
                                task_content=task_content,
                                patched_attempted=True,
                                patch_suggested_content=patch_suggested_content,
                                patch_applied_successfully=True,
                                success_after_patch=retry_res.success,
                                details_after_patch=retry_res.details
                            ))
                        else: # Should not happen if agent behaves
                            logger.error(f"No result returned after re-verifying task '{task_content}'. Treating as failure after patch.")
                            processed_results.append(TaskResult(
                                success=False, # Failed after patch attempt
                                details=current_res.details,
                                task_content=task_content,
                                patched_attempted=True,
                                patch_suggested_content=patch_suggested_content,
                                patch_applied_successfully=True, # Patch was applied
                                success_after_patch=False,
                                details_after_patch="Error: No result from agent on re-verification."
                            ))
                    else: # Patch application failed
                        processed_results.append(TaskResult(
                            success=False, # Still False as patch application failed
                            details=current_res.details,
                            task_content=task_content,
                            patched_attempted=True,
                            patch_suggested_content=patch_suggested_content,
                            patch_applied_successfully=False,
                            success_after_patch=None, # No re-verification attempted
                            details_after_patch=None
                        ))
                else: # No patch suggested
                    logger.info(f"No patch suggested for task '{task_content}'.")
                    processed_results.append(TaskResult(
                        success=False, # Still False
                        details=current_res.details,
                        task_content=task_content,
                        patched_attempted=True, # Attempted to generate
                        patch_suggested_content=None,
                        patch_applied_successfully=None,
                        success_after_patch=None,
                        details_after_patch=None
                    ))
            else: # Task was initially successful, or self_evolver is not available, or auto-patching was not attempted for other reasons
                # Ensure all fields are present in the final stored result, using defaults for patch-related fields
                processed_results.append(TaskResult(
                    success=current_res.success,
                    details=current_res.details,
                    task_content=task_content, # Use task_content from the loop context
                    patched_attempted=getattr(current_res, 'patched_attempted', False), # Keep if already set, else False
                    patch_suggested_content=getattr(current_res, 'patch_suggested_content', None),
                    patch_applied_successfully=getattr(current_res, 'patch_applied_successfully', None),
                    success_after_patch=getattr(current_res, 'success_after_patch', None),
                    details_after_patch=getattr(current_res, 'details_after_patch', None)
                ))

        # Recalculate success based on final outcomes
        successful_tasks_count = sum(1 for r in processed_results if r.success) # Final success
        failed_tasks_count = len(processed_results) - successful_tasks_count
        success_rate = (successful_tasks_count / len(processed_results)) if processed_results else 0.0

        total_elapsed_time = time.time() - start_time # Total time including patching attempts

        # Prepare results_summary with all fields from TaskResult
        results_summary_list = []
        for r in processed_results:
            results_summary_list.append({
                'task': r.task_content,
                'success': r.success, # Final success
                'details': r.details, # Original details
                'patched_attempted': r.patched_attempted,
                'patch_suggested_content': r.patch_suggested_content,
                'patch_applied_successfully': r.patch_applied_successfully,
                'success_after_patch': r.success_after_patch,
                'details_after_patch': r.details_after_patch
            })

        round_metric = {
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            'batch_size_at_round_start': self.batch_size,
            'tasks_processed_count': len(batch_tasks),
            'successful_tasks_count': successful_tasks_count, # Final successful count
            'failed_tasks_count': failed_tasks_count, # Final failed count
            'success_rate': round(success_rate, 2), # Final success rate
            'time_taken_seconds': round(total_elapsed_time, 2),
            'batch_tasks_content': batch_tasks, # Original tasks for this round
            'results_summary': results_summary_list
        }

        self.metrics_history.append(round_metric)
        self._log_metric_to_file(round_metric)

        # Adjust batch_size based on final results
        if successful_tasks_count == len(processed_results) and len(processed_results) > 0:
            self.batch_size = min(self.batch_size + 1, self.max_batch)
        elif failed_tasks_count > 1: # Consider adjusting based on initial failures vs. final failures
            self.batch_size = max(self.min_batch_size, self.batch_size - 1)

        print(f"Round completed. New Batch_size: {self.batch_size}. Processed: {len(batch_tasks)}. Final Success: {successful_tasks_count}. Final Failed: {failed_tasks_count}. Time: {total_elapsed_time:.2f}s. Final Success Rate: {success_rate:.0%}")

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус и историю последних 10 раундов из памяти."""
        return {
            "current_batch_size": self.batch_size,
            "task_queue_length": len(self.task_queue),
            "total_metrics_rounds": len(self.metrics_history),
            "last_10_rounds_metrics": self.metrics_history[-10:]
        }
