# Orchestrator Daemon - The Conductor

The Orchestrator is the "brain" and central nervous system of the Prometheus Protocol. It is responsible for managing the entire lifecycle of autonomous agents, from their conception based on declarative definitions to the real-time execution of their strategies.

## Core Responsibilities

-   **Agent Lifecycle Management:** Provides an API (`POST /agents`) to conceive new agents from a `Prometheus DSL` definition.
-   **DSL Parsing and Validation:** Uses a rich set of Pydantic models to parse and rigorously validate incoming agent definitions against the official DSL schema.
-   **Agent Runtime Execution:** For each valid agent, the Orchestrator instantiates and runs an `AgentRuntime`. This runtime is an active, living process within the Orchestrator that:
    -   Initializes and manages the agent's internal `state`.
    -   Subscribes to the NATS subjects defined in the agent's `triggers`.
    -   Executes the agent's `strategy` logic when a trigger is received.
-   **Strategy Interpretation:** Uses a `StrategyInterpreter` to translate the declarative steps of a strategy (conditions and actions) into concrete, executable operations (like checking state or publishing commands for other daemons).
-   **Event Publishing:** Publishes key events, such as `Agent.Created`, to the NATS bus to inform other parts of the system.

## API Endpoints

-   `GET /health`: Returns the health status of the daemon, including its connection to NATS.
-   `POST /agents`: Accepts a JSON object matching the `AgentDefinition` schema and starts a new agent.

## Environment Variables

-   `NATS_URL`: The URL of the NATS server. Defaults to `nats://localhost:4222`.

## Running the Daemon

For development with hot-reloading, run from the root of the repository:

```bash
uvicorn daemons.orchestrator.main:app --reload
```

For standard execution:
```bash
python -m daemons.orchestrator.main
```
