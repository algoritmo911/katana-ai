import requests
import json
import os
import shared_config

log_event = shared_config.log_event
SYNC_AGENT_LOG_PREFIX = "[SyncAgent]"

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")
API_KEY = os.environ.get("KATANA_API_KEY")

def sync_memory_with_n8n(memory_state):
    """
    Synchronizes the agent's memory state with the n8n webhook.
    """
    if not N8N_WEBHOOK_URL:
        log_event("N8N_WEBHOOK_URL not set. Skipping sync.", "warning", SYNC_AGENT_LOG_PREFIX)
        return

    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
    }

    try:
        response = requests.post(N8N_WEBHOOK_URL, data=json.dumps(memory_state), headers=headers)
        response.raise_for_status()
        log_event(f"Successfully synced memory state with n8n", "info", SYNC_AGENT_LOG_PREFIX)
    except requests.exceptions.RequestException as e:
        log_event(f"Error syncing with n8n: {e}", "error", SYNC_AGENT_LOG_PREFIX)

def periodic_sync(agent_memory_state):
    """
    This function is called periodically from the main agent loop to sync data with n8n.
    """
    log_event("Starting periodic sync with n8n...", "info", SYNC_AGENT_LOG_PREFIX)
    sync_memory_with_n8n(agent_memory_state)
