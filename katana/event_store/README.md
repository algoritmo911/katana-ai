# Katana Event Store

This directory contains the implementation of the event store for Katana. The event store is the single source of truth for all state changes in the system. It is an append-only log of events, which are small, immutable facts about what has happened.

## Architecture

The event store is based on the principles of Event Sourcing and CQRS (Command Query Responsibility Segregation).

*   **Event Sourcing:** All changes to the application state are stored as a sequence of events. The current state is derived by replaying the events.
*   **CQRS:** The responsibility for handling commands (which change the state) is separated from the responsibility for handling queries (which read the state).

## Components

*   **Event Store:** The core component that stores and retrieves events.
*   **Aggregates:** Business objects that are responsible for handling commands and generating events.
*   **Projections:** Read models that are built by listening to events from the event store.

## Getting Started

To use the event store, you need to create an instance of the `EventStore` class and then use it to append and retrieve events.

```python
from katana.event_store.event_store import EventStore

# Create an event store
event_store = EventStore()

# Append an event
event_store.append(
    event_type="COMMAND_CREATED",
    aggregate_id="command-123",
    payload={"type": "my_command", "args": {"foo": "bar"}},
)

# Retrieve events for an aggregate
events = event_store.get_events_for_aggregate("command-123")
```
