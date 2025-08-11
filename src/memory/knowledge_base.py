import os
from typing import Dict, Optional

# A simple in-memory cache for loaded knowledge files.
_knowledge_cache: Dict[str, str] = {}
KNOWLEDGE_BASE_DIR = "knowledge"

def load_knowledge(topic: str, force_reload: bool = False) -> Optional[str]:
    """
    Loads knowledge from a file corresponding to a topic.

    Args:
        topic: The topic name, which should correspond to a file in the knowledge base.
        force_reload: If True, bypass the cache and reload from disk.

    Returns:
        The content of the knowledge file as a string, or None if not found.
    """
    if topic in _knowledge_cache and not force_reload:
        return _knowledge_cache[topic]

    # Construct a plausible file path from the topic.
    # e.g., "n8n.basic_triggers" -> "knowledge/n8n/basic_triggers.md"
    file_path_parts = topic.split('.')
    file_path = os.path.join(KNOWLEDGE_BASE_DIR, *file_path_parts) + ".md"

    if not os.path.exists(file_path):
        print(f"Knowledge file not found at: {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            _knowledge_cache[topic] = content
            return content
    except IOError as e:
        print(f"Error reading knowledge file {file_path}: {e}")
        return None

def get_knowledge(topic: str) -> Optional[str]:
    """
    Retrieves knowledge about a specific topic.

    This is a simple implementation that maps a topic directly to a file.
    Future versions could use semantic search or a vector database.

    Args:
        topic: The topic to retrieve knowledge for (e.g., "n8n.basic_triggers").

    Returns:
        The knowledge content as a string, or None if not found.
    """
    return load_knowledge(topic)

if __name__ == '__main__':
    # This example assumes you run it from the root of the project
    # and have a file at "knowledge/n8n/basic_triggers.md"

    # To make this runnable, let's create a dummy file for the example
    if not os.path.exists("knowledge/n8n"):
        os.makedirs("knowledge/n8n")
    with open("knowledge/n8n/basic_triggers.md", "w") as f:
        f.write("# n8n Basic Triggers\n\n- Webhook\n- Cron Job\n- Manual Execution")

    print("--- Testing Knowledge Base ---")
    topic_name = "n8n.basic_triggers"
    knowledge_content = get_knowledge(topic_name)

    if knowledge_content:
        print(f"Successfully retrieved knowledge for topic '{topic_name}':")
        print(knowledge_content)
    else:
        print(f"Failed to retrieve knowledge for topic '{topic_name}'.")

    # Test caching
    print("\n--- Testing Cache ---")
    print("Calling get_knowledge again for the same topic...")
    cached_content = get_knowledge(topic_name)
    if "Webhook" in cached_content:
         print("Content retrieved successfully from cache.")

    # Clean up the dummy file
    os.remove("knowledge/n8n/basic_triggers.md")
