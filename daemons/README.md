# Prometheus Daemons

This directory contains the source code for the daemons that make up the Prometheus Protocol, a decentralized cognitive architecture for autonomous asset management.

## Architecture

The system is designed as a swarm of specialized, independent daemons that communicate via a NATS message bus. Each daemon is responsible for a specific cognitive function.

-   **Orchestrator:** The brain of the system. It parses strategies written in Prometheus DSL and manages the lifecycle of trading agents.
-   **Chronos:** The oracle of time. It ingests market data, manages time-series information, and emits time-based events (heartbeats).
-   **Hephaestus:** The forge. It executes actions in the outside world, such as placing trades via exchange APIs.
-   **Mnemosyne:** The scribe of memories. It records all system events and builds a knowledge graph for contextual understanding.

## Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/)
-   Python 3.10+

### Running the Infrastructure

The core infrastructure (NATS, QuestDB, Neo4j) is managed by Docker Compose. To start the services, run the following command from the root of the repository:

```bash
docker-compose up
```

This will start all the necessary services in the background.

### Running the Daemons

Each daemon can be run as a separate Python process.

**To run the Orchestrator:**

```bash
python daemons/orchestrator/main.py
```

The Orchestrator's health check will be available at `http://localhost:8000/health`.

**To run the Chronos daemon:**

```bash
python daemons/chronos/main.py
```

This will start the Chronos daemon, which will begin publishing a heartbeat to the NATS server every second.

## System Visualization (Knowledge Graph)

After running the end-to-end test (`daemons/tests/test_first_action.py`), the Mnemosyne daemon will have created a trace of the agent's first thought and action in the Neo4j database.

To visualize this:
1.  Open your web browser and navigate to the Neo4j Browser: `http://localhost:7474`.
2.  Connect to the database using the credentials `neo4j` / `password`.
3.  Run the following Cypher query in the query editor:
    ```cypher
    MATCH (n) RETURN n;
    ```
4.  This will display all the nodes and relationships created during the test, showing the full chain of events from agent conception to action execution.
