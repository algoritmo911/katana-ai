# Quickstart Guide: Katana AI Trading Bot

This guide explains how to set up the Katana AI trading bot prototype.

## Prerequisites

- Python 3.8+
- An account on Coinbase
- A Telegram account
- An n8n instance (cloud or self-hosted)

## 1. Get Coinbase API Keys

1.  Log in to your Coinbase account.
2.  Go to **Settings > API**.
3.  Click **+ New API Key**.
4.  Enable the required permissions. For this bot, you'll need:
    -   `wallet:accounts:read` (to get balance and account info)
    -   `wallet:transactions:read` (to get history)
    -   `wallet:buys:create` (to create buy orders)
    -   `wallet:sells:create` (to create sell orders)
    -   `wallet:prices:read` (to get spot prices)
5.  Securely store your **API Key** and **API Secret**.

## 2. Set up the Telegram Bot

1.  Open Telegram and search for the **BotFather**.
2.  Start a chat and send the `/newbot` command.
3.  Follow the instructions to choose a name and username for your bot.
4.  BotFather will give you a **token**. Keep it safe.

## 3. Set up the n8n Workflow

1.  Create a new workflow in your n8n instance.
2.  Add a **Webhook** node as the trigger. This will give you a webhook URL.
3.  This webhook will receive commands from the Telegram bot. For now, you can just log the data. A more advanced setup would involve calling the Coinbase API.

## 4. Configure Environment Variables

Create a `.env` file in the root of the project by copying `.env.example`. Fill in the following variables:

```
COINBASE_API_KEY="your_coinbase_api_key"
COINBASE_API_SECRET="your_coinbase_api_secret"
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
N8N_WEBHOOK_URL="your_n8n_webhook_url"
```

## 5. Installation and Running the Bot

1.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the Telegram bot:
    ```bash
    python src/katana_ai/interfaces/telegram_bot.py
    ```

Your bot should now be running and connected to Telegram. You can start a chat with it and use the `/trade` command.
