# Hephaestus Daemon - The Forge

Hephaestus is the "hands" of the Prometheus Protocol. It is a reliable and secure executor daemon that listens for action commands from agents and translates them into concrete API requests to external services like exchanges.

## Core Responsibilities

-   **Action Execution:** Subscribes to NATS subjects for action commands and executes them.
-   **Service Integration:** Uses adapters, like the `CoinbaseAdvancedClient`, to interact with external APIs.
-   **Secure Secret Management:** Fetches API keys and other secrets from a secure vault (like Doppler or HashiCorp Vault) at startup.
-   **Result Publishing:** Publishes the outcome of each action (success or failure) back to NATS for the originating agent and Mnemosyne to consume.

## NATS Subjects

-   **Listens on:** `agent.*.action.execute` (wildcard subject for all agents)
    -   This is a queue subscription to ensure actions are processed exactly once.
    -   **Example Message:**
        ```json
        {
            "type": "hephaestus.trade",
            "parameters": {
                "action": "BUY",
                "product_id": "BTC-USD",
                "amount": "0.001"
            }
        }
        ```

-   **Publishes to:** `agent.{id}.action.result`
    -   **Example Success Message:**
        ```json
        {
            "status": "SUCCESS",
            "details": {
                "order_id": "mock-order-1672531200"
            }
        }
        ```
    -   **Example Failure Message:**
        ```json
        {
            "status": "FAILURE",
            "error": "Insufficient funds"
        }
        ```

## Environment Variables

-   `DOPPLER_TOKEN`: **Required**. The service token for Doppler to fetch API secrets.
-   `NATS_URL`: The URL of the NATS server. Defaults to `nats://localhost:4222`.

## Running the Daemon

From the root of the repository:

```bash
python -m daemons.hephaestus.main
```
