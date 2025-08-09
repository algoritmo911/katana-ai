# n8n Workflow: "My workflow 3" - AI Chat & Knowledge Base

## 1. Overview
This document describes the refactored n8n workflow, "My workflow 3". This is a complex, multi-stage pipeline designed to function as an intelligent chat agent over Telegram. It can process both text and voice messages, maintain conversational memory, and use a knowledge base to answer questions.

The refactoring project focused on fixing critical bugs, implementing a functional knowledge base pipeline, and improving the overall stability and maintainability of the workflow.

## 2. Architecture & Data Flow

The workflow is now composed of three distinct pipelines:

### a) Main Chat Pipeline (Text & Voice)
This is the primary path for user interaction.
1.  **`Telegram Trigger`**: A single, webhook-based trigger receives all incoming messages.
2.  **`Switch`**: Routes the message based on content type (voice or text).
3.  **Voice Path**: If the message is a voice note, it is downloaded (`Download File`) and transcribed into text (`Transcribe`).
4.  **`Set Final Text`**: This node unifies the input, whether from a text message or transcribed voice, and prepares key variables like `sessionId`, `user_id`, `username`, etc.
5.  **`Save User Message`**: The user's message is now correctly logged to the `chat_logs` table in Supabase.
6.  **`Send Typing Action`**: A "typing..." indicator is sent to the user for better UX.
7.  **`ИНФО АГЕНТ`**: The core LangChain agent processes the user's text. It is equipped with:
    *   **Short-term Memory**: `ВРЕМЕННАЯ ПАМЯТЬ 1` (Postgres-based chat memory).
    *   **Long-term Memory**: `DATA_TOOL1` (a tool to query the Supabase vector store).
    *   **Language Model**: `МОЗГ 1` (an OpenAI GPT model).
8.  **`Response1`**: The agent's generated response is sent back to the user on Telegram.
9.  **`Save Bot Message1`**: The bot's response is logged to the `chat_logs` table in Supabase, completing the conversation loop.

### b) Knowledge Base Ingestion Pipeline
This new pipeline allows for adding new information to the agent's long-term memory.
1.  **`Add Document to Knowledge Base`**: A manual trigger to start the process. It requires the document text and optional JSON metadata.
2.  **`Create Document Embedding`**: An OpenAI node generates a vector embedding from the document text.
3.  **`Save Document to DB`**: The original text, its embedding, and metadata are saved to the `documents` table in Supabase.

### c) Error Handling Pipeline
This pipeline catches and logs errors from the main workflow.
1.  **`Error Trigger`**: A global trigger that activates on any workflow error.
2.  **`Log Error to DB`**: Saves detailed error information (message, node name, execution data) to the `error_logs` table in Supabase for debugging.

## 3. Setup and Configuration

To run this workflow, you need to configure the following credentials in your n8n instance.

### Required Credentials:
1.  **Telegram (`telegramApi`)**:
    *   **Name in workflow:** `Билл`
    *   **ID in workflow:** `HatmTi14ZGSaZx5k`
    *   **Setup:** Create a Telegram credential in n8n and provide your Telegram Bot Token.
2.  **OpenAI (`openAiApi`)**:
    *   **Name in workflow:** `OpenAi account 2`
    *   **ID in workflow:** `NVTO9nedqmqRgH9P`
    *   **Setup:** Create an OpenAI credential and provide your API key.
3.  **Supabase (`supabaseApi`)**:
    *   **Name in workflow:** `Supabase account 2`
    *   **ID in workflow:** `b95yW1FV8NuENfQk`
    *   **Setup:** Create a Supabase credential, providing your Project URL and Supabase API Key (the `service_role` key is recommended for server-side operations).
4.  **PostgreSQL (`postgres`)**:
    *   **Name in workflow:** `Postgres account`
    *   **ID in workflow:** `TvuvZ1Mm9CLMMFpo`
    *   **Setup:** Create a Postgres credential with the connection details for the database used by the Chat Memory node.

### Database Schema
Ensure your Supabase project has the following tables:
*   **`chat_logs`**: For storing conversation history. Recommended columns: `id`, `created_at`, `session_id`, `user_id`, `username`, `first_name`, `role` (e.g., 'user' or 'assistant'), `content` (text), `metadata` (json).
*   **`documents`**: For the knowledge base. This is a standard table for `pgvector`. It requires columns for `content` (text), `embedding` (vector), and `metadata` (jsonb). You must have the `pgvector` extension enabled in your Supabase database.
*   **`error_logs`**: For logging workflow errors. Recommended columns: `id`, `created_at`, `error_message`, `node_name`, `node_type`, `execution_id`, `workflow_id`, `error_data` (json).

## 4. Usage

### a) Chatting with the Bot
- Simply send a text or voice message to the connected Telegram bot. The main pipeline will be triggered.

### b) Adding to the Knowledge Base
1.  In the n8n UI, find the "Add Document to Knowledge Base" trigger.
2.  Click "Test step".
3.  Fill in the "Document Text" and optional "Document Metadata" fields.
4.  Run the trigger. The document will be processed and saved to the vector store.

## 5. Monitoring
- Errors are automatically logged to the `error_logs` table in Supabase. Regularly check this table to monitor the health of the workflow.
- The `chat_logs` table can be reviewed to ensure conversations are being logged correctly.
