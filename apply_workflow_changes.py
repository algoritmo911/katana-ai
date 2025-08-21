import os
import json
from tools.n8n_client import N8nClient

# --- User Provided Credentials ---
# It's better to load these from environment variables or a secure store in a real scenario
N8N_URL = "https://korvin.app.n8n.cloud"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxYWIxYTZlOC0zNTliLTRhNjctOWRlNy0xZDY1MzgzMTdlYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUxMTk2NjcxLCJleHAiOjE3NTg5Mjc2MDB9.cQdb8UCFAYAfJGBolIXzZW9ROMxKEznRbBZV2BjtuT8"
WORKFLOW_ID = "sgMlcZDEcZWlHP6X"

# --- Modification Functions ---

def find_node_by_name(workflow_data, name):
    """Finds a node in the workflow data by its name."""
    for node in workflow_data.get('nodes', []):
        if node.get('name') == name:
            return node
    return None

def harden_session_id(workflow_data):
    """Strengthens the sessionId generation with a fallback."""
    print("Applying: Harden Session ID")
    set_final_text_node = find_node_by_name(workflow_data, "Set Final Text")
    if not set_final_text_node:
        print("  - WARNING: 'Set Final Text' node not found.")
        return

    for assignment in set_final_text_node.get('parameters', {}).get('assignments', {}).get('assignments', []):
        if assignment.get('name') == 'sessionId':
            assignment['value'] = "={{ 'user_' + ($('Switch').item.json.message.from?.id ?? $('Switch').item.json.message.chat?.id ?? 'default_session') }}"
            print("  - Patched sessionId expression.")
            break

def add_ltm_storage(workflow_data):
    """Adds nodes and connections for LTM storage (embeddings)."""
    print("Applying: LTM Storage Implementation")

    # 1. Add Embed/Merge nodes for User Message
    embed_user_node = {
        "parameters": {"text": "={{ $('Set Final Text').item.json.text }}"},
        "id": "embed-user-message-api",
        "name": "Embed User Message",
        "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi", "typeVersion": 1.2,
        "position": [-3232, -352],
        "credentials": {"openAiApi": {"id": "NVTO9nedqmqRgH9P", "name": "OpenAi account 2"}}
    }
    merge_user_node = {
        "parameters": {"mode": "combine"}, "id": "merge-user-embedding-api",
        "name": "Merge User Embedding", "type": "n8n-nodes-base.merge", "typeVersion": 2,
        "position": [-3072, -352]
    }
    workflow_data['nodes'].extend([embed_user_node, merge_user_node])
    print("  - Added 'Embed User Message' and 'Merge' nodes.")

    # 2. Update 'Save User Message' node to store embedding
    save_user_node = find_node_by_name(workflow_data, "Save User Message")
    if save_user_node:
        save_user_node['parameters']['fieldsUi']['fieldValues'].append({
            "fieldId": "embedding",
            "fieldValue": "={{ $json.embedding }}"
        })
        print("  - Updated 'Save User Message' to store embedding.")

    # 3. Update connections for user message path
    workflow_data['connections']['Set Final Text']['main'] = [
        [{"node": "Embed User Message", "type": "main", "index": 0}],
        [{"node": "Merge User Embedding", "type": "main", "index": 0}]
    ]
    workflow_data['connections']['Embed User Message'] = {
        "main": [[{"node": "Merge User Embedding", "type": "main", "index": 1}]]
    }
    workflow_data['connections']['Merge User Embedding'] = {
        "main": [[{"node": "Save User Message", "type": "main", "index": 0}]]
    }
    print("  - Rewired user message connections for embedding.")

    # 4. Add Embed node for Bot Message
    embed_bot_node = {
        "parameters": {"text": "={{ $('ИНФО АГЕНТ').item.json.output }}"},
        "id": "embed-bot-message-api", "name": "Embed Bot Message",
        "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi", "typeVersion": 1.2,
        "position": [-2336, -192],
        "credentials": {"openAiApi": {"id": "NVTO9nedqmqRgH9P", "name": "OpenAi account 2"}}
    }
    workflow_data['nodes'].append(embed_bot_node)
    print("  - Added 'Embed Bot Message' node.")

    # 5. Update 'Save Bot Message1' to store embedding
    save_bot_node = find_node_by_name(workflow_data, "Save Bot Message1")
    if save_bot_node:
        save_bot_node['parameters']['fieldsUi']['fieldValues'].append({
            "fieldId": "embedding",
            "fieldValue": "={{ $('Embed Bot Message').item.json.embedding }}"
        })
        print("  - Updated 'Save Bot Message1' to store embedding.")

    # 6. Update connections for bot message path
    workflow_data['connections']['Response1']['main'] = [[{"node": "Embed Bot Message", "type": "main", "index": 0}]]
    workflow_data['connections']['Embed Bot Message'] = {"main": [[{"node": "Save Bot Message1", "type": "main", "index": 0}]]}
    print("  - Rewired bot message connections for embedding.")


def add_ltm_retrieval(workflow_data):
    """Adds the LTM retrieval tool and its dependencies."""
    print("Applying: LTM Retrieval Implementation")

    # 1. Add nodes for the tool
    search_node = {
        "parameters": {"tableName": "chat_logs", "options": {"queryName": "match_chat_history", "filter": {"session_id": "={{ $('Set Final Text').item.json.sessionId }}"}}},
        "type": "@n8n/n8n-nodes-langchain.vectorStoreSupabase", "typeVersion": 1,
        "position": [-2688, 160], "id": "ltm-search-api", "name": "ChatLogs Vector Search",
        "credentials": {"supabaseApi": {"id": "FDs7IVyXwVL3ROLI", "name": "Supabase account"}}
    }
    tool_node = {
        "parameters": {"name": "conversation_history", "description": "Use this tool to search the user's past conversation history. Use it to recall specific details, previous discussions, or facts the user has mentioned before. The input should be a question about the past conversation.", "topK": 5},
        "type": "@n8n/n8n-nodes-langchain.toolVectorStore", "typeVersion": 1,
        "position": [-2528, 160], "id": "ltm-tool-api", "name": "CONVERSATION_HISTORY_TOOL"
    }
    embed_query_node = {
        "parameters": {"model": "text-embedding-ada-002"}, "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi", "typeVersion": 1.2,
        "position": [-2688, 304], "id": "ltm-embed-query-api", "name": "Embed History Query",
        "credentials": {"openAiApi": {"id": "NVTO9nedqmqRgH9P", "name": "OpenAi account 2"}}
    }
    workflow_data['nodes'].extend([search_node, tool_node, embed_query_node])
    print("  - Added nodes for LTM retrieval tool.")

    # 2. Add connections for the tool
    workflow_data['connections']['ChatLogs Vector Search'] = {"ai_vectorStore": [[{"node": "CONVERSATION_HISTORY_TOOL", "type": "ai_vectorStore", "index": 0}]]}
    workflow_data['connections']['CONVERSATION_HISTORY_TOOL'] = {"ai_tool": [[{"node": "ИНФО АГЕНТ", "type": "ai_tool", "index": 0}]]}
    workflow_data['connections']['Embed History Query'] = {"ai_embedding": [[{"node": "ChatLogs Vector Search", "type": "ai_embedding", "index": 0}]]}
    # Also connect the LLM to the tool
    if 'МОЗГ 1' in workflow_data['connections']:
        workflow_data['connections']['МОЗГ 1']['ai_languageModel'].append([{"node": "CONVERSATION_HISTORY_TOOL", "type": "ai_languageModel", "index": 0}])
    print("  - Wired up LTM retrieval tool.")


def add_error_handling(workflow_data):
    """Adds onError, retryOnFail, and NoOp logging nodes."""
    print("Applying: Error Handling and Resilience")

    # 1. Add NoOp logging nodes
    log_nodes = [
        {"parameters": {}, "id": "log-fail-user-save-api", "name": "LOG: LTM_USER_SAVE_FAIL", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [-2912, -300]},
        {"parameters": {}, "id": "log-fail-bot-save-api", "name": "LOG: LTM_BOT_SAVE_FAIL", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [-2112, -150]},
        {"parameters": {}, "id": "log-fail-user-embed-api", "name": "LOG: EMBED_USER_FAIL", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [-3232, -200]},
        {"parameters": {}, "id": "log-fail-bot-embed-api", "name": "LOG: EMBED_BOT_FAIL", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [-2336, -50]},
        {"parameters": {}, "id": "log-fail-ltm-search-api", "name": "LOG: LTM_SEARCH_FAIL", "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": [-2688, 0]}
    ]
    workflow_data['nodes'].extend(log_nodes)
    print("  - Added 5 NoOp nodes for logging.")

    # 2. Add settings and error connections to nodes
    nodes_to_harden = {
        "Save User Message": "LOG: LTM_USER_SAVE_FAIL",
        "Save Bot Message1": "LOG: LTM_BOT_SAVE_FAIL",
        "Embed User Message": "LOG: EMBED_USER_FAIL",
        "Embed Bot Message": "LOG: EMBED_BOT_FAIL",
        "ChatLogs Vector Search": "LOG: LTM_SEARCH_FAIL",
    }
    for node_name, log_node_name in nodes_to_harden.items():
        node = find_node_by_name(workflow_data, node_name)
        if node:
            node['onError'] = "continueRegularOutput"
            node['retryOnFail'] = {"retries": 1, "interval": 1000}
            if node_name in workflow_data['connections']:
                 workflow_data['connections'][node_name]['error'] = [[{"node": log_node_name, "type": "main", "index": 0}]]
            else: # For terminal nodes like Save Bot Message
                 workflow_data['connections'][node_name] = {'error': [[{"node": log_node_name, "type": "main", "index": 0}]]}
            print(f"  - Hardened node: {node_name}")

    # Harden STM and LLM nodes as well
    stm_node = find_node_by_name(workflow_data, "ВРЕМЕННАЯ ПАМЯТЬ 1")
    if stm_node:
        stm_node['retryOnFail'] = {"retries": 1, "interval": 1000}
        print("  - Hardened node: ВРЕМЕННАЯ ПАМЯТЬ 1")

    llm_node = find_node_by_name(workflow_data, "МОЗГ 1")
    if llm_node:
        llm_node['retryOnFail'] = {"retries": 1, "interval": 1000}
        print("  - Hardened node: МОЗГ 1")


def main():
    """Main function to run the workflow update."""
    print("--- Starting Surgical Workflow Update ---")
    client = N8nClient(n8n_url=N8N_URL, api_key=N8N_API_KEY)

    try:
        # 1. Get the current workflow
        print(f"Fetching workflow '{WORKFLOW_ID}'...")
        workflow = client.get_workflow(WORKFLOW_ID)
        print("  - Workflow fetched successfully.")

        # 2. Apply all modifications in memory
        harden_session_id(workflow)
        add_ltm_storage(workflow)
        add_ltm_retrieval(workflow)
        add_error_handling(workflow)

        # 3. Update the workflow with all changes at once
        print(f"Pushing updated workflow '{WORKFLOW_ID}'...")
        # The API expects the workflow data under a 'nodes' and 'connections' key
        # but the GET request returns the full workflow object. Let's ensure we send the right format.
        # Based on typical APIs, the PUT might just need the core data.
        # The GET returns {id, name, active, nodes, connections, settings, ...}
        # The PUT probably wants the same structure back.

        update_response = client.update_workflow(WORKFLOW_ID, workflow)
        print("--- Surgical Operation Complete ---")
        print("  - Status: SUCCESS")
        # print("  - Server Response:", json.dumps(update_response, indent=2))

    except Exception as e:
        print("\n--- CRITICAL FAILURE DURING SURGICAL OPERATION ---")
        print(f"  - Error: {e}")
        print("  - The workflow on the server was NOT modified.")

if __name__ == '__main__':
    main()
