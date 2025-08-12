import os
import json
from pathlib import Path
import time

from bot.knowledge.graph_db import get_graph_db, close_graph_db

# --- Configuration ---
HISTORY_DIR = Path('chat_history')
STATE_FILE = Path('bot/knowledge/processing_state.json')
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_processing_state():
    """Loads the processing state from the state file."""
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_processing_state(state):
    """Saves the processing state to the state file."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def extract_triples_from_text(text):
    """
    Placeholder for LLM call to extract knowledge triples.
    This will be replaced with a real call to an LLM.
    """
    # --- LLM Call Placeholder ---
    # For now, let's simulate an extraction for a specific text.
    if "Жюль" in text and "Кузница" in text:
        print(f"Simulating LLM extraction for: {text}")
        return [
            {
                "subject": {"name": "Jules", "type": "Person"},
                "verb": "WORKS_ON",
                "object": {"name": "Project Kuznitsa", "type": "Project"}
            }
        ]
    return []

def process_history_files():
    """
    Scans history files, processes new messages, and updates the graph.
    """
    print("Starting knowledge extraction process...")
    state = load_processing_state()
    graph = get_graph_db()

    try:
        for history_file in HISTORY_DIR.glob('*_history.json'):
            filename = history_file.name
            last_processed_index = state.get(filename, -1)

            with open(history_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)

            new_messages = messages[last_processed_index + 1:]

            if not new_messages:
                continue

            print(f"Found {len(new_messages)} new messages in {filename}")

            for i, message in enumerate(new_messages):
                # We only care about messages from 'user'
                if message.get('user') != 'user':
                    continue

                text_to_process = message.get('text', '')
                triples = extract_triples_from_text(text_to_process)

                for triple in triples:
                    try:
                        graph.add_triple(triple['subject'], triple['verb'], triple['object'])
                    except Exception as e:
                        print(f"Error adding triple to graph: {e}")

                # Update state after processing each message
                state[filename] = last_processed_index + 1 + i
                save_processing_state(state)

    finally:
        close_graph_db()
        print("Knowledge extraction process finished.")

if __name__ == '__main__':
    # This allows running the extractor manually.
    # In a real system, this would be triggered by a scheduler (e.g., Celery, cron).
    process_history_files()
