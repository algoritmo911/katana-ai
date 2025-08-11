# src/dao/dao_task_handler.py
import json
import random
from typing import List, Dict, Any, Optional

# Import the new knowledge base function
from src.memory.knowledge_base import get_knowledge
# Import MemoryManager for type hinting
from src.memory.memory_manager import MemoryManager


def fetch_tasks_from_colony(
    endpoint: str = None,
    api_key: str = None,
    memory_manager: Optional[MemoryManager] = None,
    chat_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetches tasks from a backend or generates mock tasks based on knowledge and memory.
    """
    if endpoint:
        # TODO: Implement actual API call to Colony
        # Example:
        # headers = {"Authorization": f"Bearer {api_key}"}
        # response = requests.get(f"{endpoint}/tasks", headers=headers)
        # response.raise_for_status()
        # return response.json().get("tasks", [])
        print(f"Attempting to fetch tasks from Colony endpoint: {endpoint} (Not implemented yet)")
        return [{"id": "colony_task_123", "type": "data_processing", "payload": {"data_url": "http://example.com/data.zip"}, "status": "mock"}] # Placeholder
    else:
        # Generate a dynamic mock task based on the knowledge base and recent memory.
        print("Generating dynamic DAO task from knowledge base and memory.")

        # Default description
        task_description = "Create an n8n workflow based on available documentation."

        # Check memory for user's last message to make the task more relevant
        if memory_manager and chat_id:
            history = memory_manager.get_history(chat_id, limit=1)
            if history:
                last_message = history[0]
                if last_message.get('role') == 'user':
                    user_prompt = last_message.get('content', '')
                    if user_prompt:
                        print(f"DAO received user prompt from memory: '{user_prompt}'")
                        # Incorporate user prompt into the task description
                        task_description = f"Based on the user prompt '{user_prompt}', create a relevant n8n workflow."

        # Use knowledge base to add more context
        knowledge_content = get_knowledge("n8n.basic_triggers")
        if knowledge_content:
            potential_triggers = [line.strip('* ').split(':')[0] for line in knowledge_content.split('\n') if line.strip().startswith('*')]
            if potential_triggers:
                chosen_trigger = random.choice(potential_triggers)
                task_description += f" Consider using a '{chosen_trigger}' trigger."

        task_id = f"dynamic_task_{random.randint(1000, 9999)}"
        new_task = {
            "id": task_id,
            "type": "n8n_workflow_generation",
            "description": task_description,
            "source": "dao_memory_and_knowledge",
            "status": "pending"
        }

        return [new_task]

if __name__ == '__main__':
    # Example usage
    print("--- Fetching task without memory ---")
    mock_tasks = fetch_tasks_from_colony()
    print(json.dumps(mock_tasks, indent=2))

    print("\n--- Fetching task with memory ---")
    # This requires a running Redis instance for the MemoryManager to connect to.
    # We will simulate a MemoryManager for the example if Redis is not available.
    try:
        mm = MemoryManager()
        if not mm.redis_client:
            raise ConnectionError("Could not connect to Redis for example.")

        test_chat_id = "test_chat_for_dao"
        mm.add_message_to_history(test_chat_id, {"role": "user", "content": "I need to process payments with Stripe."})

        memory_tasks = fetch_tasks_from_colony(memory_manager=mm, chat_id=test_chat_id)
        print(json.dumps(memory_tasks, indent=2))

        # Clean up
        mm.clear_history(test_chat_id)

    except Exception as e:
        print(f"Could not run memory-based DAO example. Is Redis running? Error: {e}")
        print("This is expected if you are running without a Redis server.")
        # Create a mock task to show the format
        mock_memory_task = {
            "id": "mock_memory_task_123",
            "type": "n8n_workflow_generation",
            "description": "Based on the user prompt 'I need to process payments with Stripe.', create a relevant n8n workflow. Consider using a 'Webhook' trigger."
        }
        print(json.dumps([mock_memory_task], indent=2))
