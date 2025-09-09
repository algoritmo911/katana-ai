# Chronos Daemon - The Oracle of Time

Chronos is the "sensory organ" of the Prometheus Protocol. It has evolved from a simple heartbeat generator into a full market data oracle, responsible for ingesting, storing, and distributing time-series data from various external sources.

## Core Responsibilities

-   **Data Ingestion:** Connects to real-time data streams from exchanges (e.g., Coinbase WebSocket) to receive market data like trades, tickers, and order book updates.
-   **Time-Series Storage:** Parses, validates, and stores ingested data in a high-performance time-series database (QuestDB).
-   **Event Publishing:** Publishes two types of events to NATS:
    1.  A global, rhythmic **heartbeat** (`chronos.tick.1s`) that agents can use for time-based triggers.
    2.  **Market data events** (`chronos.market.ticker.{product_id}`) for each new piece of data received, allowing agents to react to market changes in real-time.
-   **Data API (Future):** Will provide a high-performance API (e.g., gRPC) for other daemons to query historical data.

## NATS Subjects

-   **Publishes to:**
    -   `chronos.tick.1s`: A global heartbeat published every second.
        -   **Message:** The current Unix timestamp as a string.
    -   `chronos.market.ticker.{product_id}`: Published for each new ticker message received.
        -   **Example Subject:** `chronos.market.ticker.BTC-USD`
        -   **Message:** A JSON object representing the `TickerData` model.

## Environment Variables

-   `NATS_URL`: The URL of the NATS server. Defaults to `nats://localhost:4222`.
-   `QUESTDB_CONN_STRING`: The connection string for the QuestDB database. Defaults to `user=admin password=quest host=localhost port=8812 dbname=qdb`.
-   `COINBASE_WS_URL`: The URL for the Coinbase Pro WebSocket feed. Defaults to `wss://ws-feed.pro.coinbase.com`.

## Running the Daemon

From the root of the repository:

```bash
python -m daemons.chronos.main
```
