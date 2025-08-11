import asyncio
import logging
from typing import List, Dict, Any, Coroutine

from katana.task_queue.service import TaskQueueService
from katana.task_queue.broker import AbstractBroker
from katana.task_queue.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    The OrchestratorAgent is responsible for decomposing complex tasks,
    dispatching them to worker agents, and synthesizing the results.
    """

    def __init__(self, task_queue_service: TaskQueueService, broker: AbstractBroker):
        """
        Initializes the OrchestratorAgent.
        Args:
            task_queue_service: An instance of TaskQueueService to send tasks.
            broker: An instance of a broker to check task statuses and results.
        """
        self.task_queue_service = task_queue_service
        self.broker = broker
        logger.info("OrchestratorAgent initialized.")

    def _decompose_task(self, complex_query: str) -> List[Dict[str, Any]]:
        """
        Decomposes a complex query into a list of atomic sub-tasks.
        This is a simplified, rule-based implementation.
        """
        sub_tasks = []
        if "новости" in complex_query.lower() and "nvidia" in complex_query.lower():
            sub_tasks.append(
                {
                    "name": "web_search",
                    "payload": {"query": "Nvidia news last 24 hours"},
                }
            )

        if (
            "финансовые отчеты" in complex_query.lower()
            and "nvidia" in complex_query.lower()
        ):
            sub_tasks.append(
                {
                    "name": "financial_data_api",
                    "payload": {"company": "NVDA", "report": "Q3"},
                }
            )

        if "прогноз" in complex_query.lower() and "акци" in complex_query.lower():
            sub_tasks.append(
                {
                    "name": "predictive_analysis",
                    "payload": {
                        "data_sources": ["web_search_result", "financial_data_result"],
                        "target": "NVDA stock price next week",
                    },
                }
            )

        logger.info(
            f"Decomposed query '{complex_query}' into {len(sub_tasks)} sub-tasks."
        )
        return sub_tasks

    def _synthesize_results(self, results: List[Any]) -> str:
        """
        Synthesizes the results from sub-tasks into a final, coherent answer.
        This is a simplified implementation.
        """
        if not results:
            return "Не удалось получить результаты для составления ответа."

        final_report = "--- Итоговый отчет ---\n\n"
        for i, res in enumerate(results):
            final_report += f"Источник {i+1}:\n"
            final_report += f'"{str(res)}"\n\n'

        final_report += "--- Конец отчета ---"
        logger.info("Successfully synthesized results into a final report.")
        return final_report

    async def handle_complex_query(self, query: str) -> str:
        """
        Handles a complex query by decomposing it, dispatching sub-tasks,
        waiting for the results, and synthesizing them into a final answer.
        """
        logger.info(f"Handling complex query: {query}")
        sub_tasks_to_dispatch = self._decompose_task(query)

        if not sub_tasks_to_dispatch:
            msg = f"Could not decompose the query: '{query}'. No sub-tasks generated."
            logger.warning(msg)
            return msg

        enqueued_tasks: List[Task] = []
        for task_info in sub_tasks_to_dispatch:
            try:
                task_obj = await self.task_queue_service.add_task(
                    name=task_info["name"],
                    payload=task_info["payload"],
                    priority=1,  # Default priority for sub-tasks
                )
                enqueued_tasks.append(task_obj)
            except Exception as e:
                logger.error(
                    f"Failed to enqueue sub-task '{task_info['name']}': {e}",
                    exc_info=True,
                )

        if not enqueued_tasks:
            return "Не удалось поставить подзадачи в очередь."

        logger.info(
            f"Successfully enqueued {len(enqueued_tasks)} sub-tasks. Now waiting for results..."
        )

        # Asynchronously wait for all tasks to complete
        results = await self._wait_for_task_results(enqueued_tasks)

        # Synthesize the final report
        final_report = self._synthesize_results(results)

        return final_report

    async def _wait_for_task_results(self, tasks: List[Task]) -> List[Any]:
        """
        Polls the broker for the status of tasks and collects their results
        once they are all completed.
        """
        task_ids = {task.id for task in tasks}
        results = {}

        POLL_INTERVAL = 2  # seconds
        TIMEOUT = 120  # seconds

        start_time = asyncio.get_event_loop().time()
        total_tasks = len(tasks)

        while len(results) < total_tasks:
            if asyncio.get_event_loop().time() - start_time > TIMEOUT:
                logger.error(f"Timeout of {TIMEOUT}s exceeded waiting for tasks.")
                break

            for task_id in list(task_ids):
                # Check if we already have a result for this task
                if task_id in results:
                    continue

                try:
                    task_state = await self.broker.get_task(task_id)
                    if task_state and task_state.status == TaskStatus.COMPLETED:
                        logger.info(
                            f"Task {task_id} completed with result: {task_state.result}"
                        )
                        results[task_id] = task_state.result
                    elif task_state and task_state.status == TaskStatus.FAILED:
                        logger.error(
                            f"Sub-task {task_id} failed. It will be excluded from the final report."
                        )
                        results[task_id] = f"ERROR: Task {task_state.name} failed."

                except Exception as e:
                    logger.error(
                        f"Error checking status for task {task_id}: {e}", exc_info=True
                    )

            if len(results) < len(tasks):
                await asyncio.sleep(POLL_INTERVAL)

        # Return results in the original order of the tasks
        return [results.get(task.id, "ERROR: Result not found") for task in tasks]
