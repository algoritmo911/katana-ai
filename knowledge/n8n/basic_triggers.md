# n8n Basic Triggers

This document outlines the fundamental triggers available in n8n for starting a workflow.

## Core Triggers

*   **Webhook:** Starts a workflow when an HTTP request is received at a specific URL. This is ideal for integrations with other services that can send webhooks.
*   **Cron Job:** Executes a workflow on a schedule (e.g., every hour, once a day). Useful for routine tasks like generating daily reports.
*   **Manual Execution:** The workflow is started manually by clicking the "Execute Workflow" button in the n8n editor. Primarily used for testing and development.

## Application-Specific Triggers

Many n8n nodes for specific applications (like Telegram, Google Sheets, etc.) have their own triggers. For example:
*   **Telegram Trigger:** Starts a workflow when a new message is received by the bot.
*   **Google Sheet Trigger:** Starts a workflow when a new row is added to a specified sheet.
