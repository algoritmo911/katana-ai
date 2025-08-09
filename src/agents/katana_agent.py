import asyncio
import json
import os
from typing import List, Dict, Any

from src.orchestrator.task_orchestrator import TaskResult
from src.memory.memory_manager import MemoryManager

# Placeholder for the NLP response function, similar to katana_bot.py
def get_katana_response(history: list[dict]) -> str:
    """Placeholder for the function that gets a response from an NLP model."""
    print(f"get_katana_response called with history: {history}")
    if not history:
        return "Катана к вашим услугам. О чём поразмыслим?"
    last_message = history[-1]['content']
    return f"Размышляю над вашим последним сообщением: '{last_message}'... (это заглушка)"

MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"

class KatanaAgent:
    def __init__(self):
        """
        Initializes the KatanaAgent.
        """
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        redis_db = int(os.getenv('REDIS_DB', '0'))
        chat_ttl_str = os.getenv('REDIS_CHAT_HISTORY_TTL_SECONDS')
        chat_ttl = int(chat_ttl_str) if chat_ttl_str else None

        self.memory_manager = MemoryManager(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            chat_history_ttl_seconds=chat_ttl
        )
        print(f"KatanaAgent initialized with MemoryManager connected to {redis_host}:{redis_port}")

    async def process_chat_message(self, chat_id: str, user_message: str) -> str:
        """
        Handles a single interactive chat message.
        This is the primary method for the n8n integration.
        """
        print(f"Processing message for chat_id {chat_id}: '{user_message}'")

        # 1. Retrieve history
        current_history = self.memory_manager.get_history(chat_id)
        print(f"Retrieved history for chat_id {chat_id}. Length: {len(current_history)}")

        # 2. Add user message to history
        self.memory_manager.add_message_to_history(chat_id, {"role": MESSAGE_ROLE_USER, "content": user_message})

        # The history for the model should include the new message
        history_for_model = self.memory_manager.get_history(chat_id)

        # 3. Get response from NLP model
        katana_response_text = get_katana_response(history_for_model)
        print(f"Katana response for chat_id {chat_id}: {katana_response_text}")

        # 4. Save assistant response to history
        self.memory_manager.add_message_to_history(chat_id, {"role": MESSAGE_ROLE_ASSISTANT, "content": katana_response_text})
        print(f"Appended assistant response to history for chat_id {chat_id}.")

        # 5. Return the response
        return katana_response_text

    # This method is for the TaskOrchestrator, which processes background tasks.
    # We need to define what a "task" is in this context.
    # For now, we'll assume a task is a JSON string with a 'command' and 'payload'.
    async def handle_single_task(self, task: str) -> TaskResult:
        """
        Processes a single background task.
        """
        print(f"KatanaAgent handling background task: {task}")
        await asyncio.sleep(0.1) # Simulate async work

        try:
            task_data = json.loads(task)
            # TODO: Implement logic for different background commands
            # e.g., task_data['command'] == 'summarize_chat'
            details = f"Successfully processed command: {task_data.get('command', 'unknown')}"
            is_success = True
        except json.JSONDecodeError:
            details = "Failed to parse task as JSON."
            is_success = False
        except Exception as e:
            details = f"An error occurred: {e}"
            is_success = False

        print(details)
        return TaskResult(success=is_success, details=details, task_content=task)

    async def process_tasks(self, tasks: List[str]) -> List[TaskResult]:
        """
        Processes a list of background tasks in parallel.
        This method is called by the TaskOrchestrator.
        """
        if not tasks:
            return []

        print(f"KatanaAgent received a batch of {len(tasks)} background tasks.")
        results = await asyncio.gather(*(self.handle_single_task(task) for task in tasks))
        return results
