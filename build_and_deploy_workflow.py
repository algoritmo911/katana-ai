import os
import json
from tools.n8n_client import N8nClient

# --- Config ---
N8N_URL = "https://korvin.app.n8n.cloud"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxYWIxYTZlOC0zNTliLTRhNjctOWRlNy0xZDY1MzgzMTdlYjkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzUxMTk2NjcxLCJleHAiOjE3NTg5Mjc2MDB9.cQdb8UCFAYAfJGBolIXzZW9ROMxKEznRbBZV2BjtuT8"
WORKFLOW_ID = "sgMlcZDEcZWlHP6X"
SOURCE_FILE = "clean_workflow.json"

# --- Modification Functions ---

def find_node_by_name(workflow_data, name):
    for node in workflow_data.get('nodes', []):
        if node.get('name') == name:
            return node
    return None

def harden_session_id(workflow_data):
    print("Applying: Harden Session ID")
    node = find_node_by_name(workflow_data, "Set Final Text")
    if not node:
        print("  - WARNING: 'Set Final Text' node not found.")
        return
    for assignment in node['parameters']['assignments']['assignments']:
        if assignment.get('name') == 'sessionId':
            assignment['value'] = "={{ 'user_' + ($('Switch').item.json.message.from?.id ?? $('Switch').item.json.message.chat?.id ?? 'default_session') }}"
            print("  - Patched sessionId expression.")
            break

def add_ltm_storage(workflow_data):
    print("Applying: LTM Storage")
    embed_user = {"parameters": {"text": "={{ $('Set Final Text').item.json.text }}"}, "id": "embed-user-api", "name": "Embed User Message", "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi", "typeVersion": 1.2, "position": [-3232, -352], "credentials": {"openAiApi": {"id": "NVTO9nedqmqRgH9P", "name": "OpenAi account 2"}}}
    merge_user = {"parameters": {"mode": "combine"}, "id": "merge-user-api", "name": "Merge User Embedding", "type": "n8n-nodes-base.merge", "typeVersion": 2, "position": [-3072, -352]}
    embed_bot = {"parameters": {"text": "={{ $('ИНФО АГЕНТ').item.json.output }}"}, "id": "embed-bot-api", "name": "Embed Bot Message", "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi", "typeVersion": 1.2, "position": [-2336, -192], "credentials": {"openAiApi": {"id": "NVTO9nedqmqRgH9P", "name": "OpenAi account 2"}}}
    workflow_data['nodes'].extend([embed_user, merge_user, embed_bot])
    print("  - Added embedding/merge nodes.")

    find_node_by_name(workflow_data, "Save User Message")['parameters']['fieldsUi']['fieldValues'].append({"fieldId": "embedding", "fieldValue": "={{ $json.embedding }}"})
    find_node_by_name(workflow_data, "Save Bot Message1")['parameters']['fieldsUi']['fieldValues'].append({"fieldId": "embedding", "fieldValue": "={{ $('Embed Bot Message').item.json.embedding }}"})
    print("  - Updated save nodes with embedding field.")

    workflow_data['connections']['Set Final Text']['main'] = [[{"node": "Embed User Message", "type": "main", "index": 0}], [{"node": "Merge User Embedding", "type": "main", "index": 0}]]
    workflow_data['connections']['Embed User Message'] = {"main": [[{"node": "Merge User Embedding", "type": "main", "index": 1}]]}
    workflow_data['connections']['Merge User Embedding'] = {"main": [[{"node": "Save User Message", "type": "main", "index": 0}]]}
    workflow_data['connections']['Response1']['main'] = [[{"node": "Embed Bot Message", "type": "main", "index": 0}]]
    workflow_data['connections']['Embed Bot Message'] = {"main": [[{"node": "Save Bot Message1", "type": "main", "index": 0}]]}
    print("  - Updated connections for LTM storage.")

def add_ltm_retrieval(workflow_data):
    print("Applying: LTM Retrieval Tool")
    search_node = {"parameters": {"tableName": "chat_logs", "options": {"queryName": "match_chat_history"}}, "type": "@n8n/n8n-nodes-langchain.vectorStoreSupabase", "typeVersion": 1, "position": [-2688, 160], "id": "ltm-search-api", "name": "ChatLogs Vector Search", "credentials": {"supabaseApi": {"id": "FDs7IVyXwVL3ROLI", "name": "Supabase account"}}}
    tool_node = {"parameters": {"name": "conversation_history", "description": "Use this tool to search the user's past conversation history.", "topK": 5}, "type": "@n8n/n8n-nodes-langchain.toolVectorStore", "typeVersion": 1, "position": [-2528, 160], "id": "ltm-tool-api", "name": "CONVERSATION_HISTORY_TOOL"}
    embed_query_node = {"parameters": {}, "type": "@n8n/n8n-nodes-langchain.embeddingsOpenAi", "typeVersion": 1.2, "position": [-2688, 304], "id": "ltm-embed-query-api", "name": "Embed History Query", "credentials": {"openAiApi": {"id": "NVTO9nedqmqRgH9P", "name": "OpenAi account 2"}}}
    workflow_data['nodes'].extend([search_node, tool_node, embed_query_node])
    print("  - Added LTM tool nodes.")

    workflow_data['connections']['ChatLogs Vector Search'] = {"ai_vectorStore": [[{"node": "CONVERSATION_HISTORY_TOOL", "type": "ai_vectorStore", "index": 0}]]}
    # CORRECTED INDEX FROM 0 to 1
    workflow_data['connections']['CONVERSATION_HISTORY_TOOL'] = {"ai_tool": [[{"node": "ИНФО АГЕНТ", "type": "ai_tool", "index": 1}]]}
    workflow_data['connections']['Embed History Query'] = {"ai_embedding": [[{"node": "ChatLogs Vector Search", "type": "ai_embedding", "index": 0}]]}
    if 'МОЗГ 1' in workflow_data['connections']:
        workflow_data['connections']['МОЗГ 1']['ai_languageModel'].append([{"node": "CONVERSATION_HISTORY_TOOL", "type": "ai_languageModel", "index": 0}])
    print("  - Updated connections for LTM tool (with corrected index).")

def add_error_handling(workflow_data):
    print("Applying: Error Handling")
    log_nodes_data = [
        {"id": "log-user-save-api", "name": "LOG: LTM_USER_SAVE_FAIL", "pos": [-2912, -300]},
        {"id": "log-bot-save-api", "name": "LOG: LTM_BOT_SAVE_FAIL", "pos": [-2112, -150]},
        {"id": "log-user-embed-api", "name": "LOG: EMBED_USER_FAIL", "pos": [-3232, -200]},
        {"id": "log-bot-embed-api", "name": "LOG: EMBED_BOT_FAIL", "pos": [-2336, -50]},
        {"id": "log-ltm-search-api", "name": "LOG: LTM_SEARCH_FAIL", "pos": [-2688, 0]}
    ]
    for data in log_nodes_data:
        workflow_data['nodes'].append({"parameters": {}, "id": data["id"], "name": data["name"], "type": "n8n-nodes-base.noOp", "typeVersion": 1, "position": data["pos"]})
    print("  - Added NoOp logging nodes.")

    nodes_to_harden = {
        "Save User Message": "LOG: LTM_USER_SAVE_FAIL", "Save Bot Message1": "LOG: LTM_BOT_SAVE_FAIL",
        "Embed User Message": "LOG: EMBED_USER_FAIL", "Embed Bot Message": "LOG: EMBED_BOT_FAIL",
        "ChatLogs Vector Search": "LOG: LTM_SEARCH_FAIL"
    }
    for node_name, log_node_name in nodes_to_harden.items():
        node = find_node_by_name(workflow_data, node_name)
        if node:
            node['onError'] = "continueRegularOutput"
            node['retryOnFail'] = {"retries": 1, "interval": 1000}
            if node_name in workflow_data['connections']:
                 workflow_data['connections'][node_name]['error'] = [[{"node": log_node_name, "type": "main", "index": 0}]]
            else:
                 workflow_data['connections'][node_name] = {'error': [[{"node": log_node_name, "type": "main", "index": 0}]]}
            print(f"  - Hardened '{node_name}'.")

    for node_name in ["ВРЕМЕННАЯ ПАМЯТЬ 1", "МОЗГ 1"]:
        node = find_node_by_name(workflow_data, node_name)
        if node:
            node['retryOnFail'] = {"retries": 1, "interval": 1000}
            print(f"  - Hardened '{node_name}'.")

def main():
    print("--- Starting Architect Protocol (Final Attempt) ---")
    client = N8nClient(n8n_url=N8N_URL, api_key=N8N_API_KEY)

    try:
        print(f"Loading base workflow from '{SOURCE_FILE}'...")
        with open(SOURCE_FILE, 'r') as f:
            workflow_data = json.load(f)
        print("  - Base workflow loaded.")

        # Apply all modifications in memory
        harden_session_id(workflow_data)
        add_ltm_storage(workflow_data)
        add_ltm_retrieval(workflow_data)
        add_error_handling(workflow_data)

        # Deploy the final, complete workflow
        print(f"Deploying final workflow to ID '{WORKFLOW_ID}'...")
        client.update_workflow(WORKFLOW_ID, workflow_data)
        print("--- Architect Protocol Complete ---")
        print("  - Status: SUCCESS. Workflow has been built and deployed.")

    except Exception as e:
        print("\n--- CRITICAL FAILURE DURING DEPLOYMENT ---")
        print(f"  - Error: {e}")

if __name__ == '__main__':
    main()
