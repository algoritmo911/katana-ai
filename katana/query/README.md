# Katana Query

This directory contains the implementation of the query side of the CQRS architecture for Katana. The query side is responsible for providing read-only access to the application state.

## Architecture

The query side is based on the concept of projections. A projection is a read model that is built by listening to events from the event store. Each projection is tailored to a specific query or set of queries.

## Components

*   **Projections:** Read models that are built by listening to events from the event store.
*   **Query Handlers:** Components that are responsible for handling queries and returning data from the projections.

## Getting Started

To use the query side, you need to create an instance of a projection and then use it to build the read model.

```python
from katana.event_store.event_store import EventStore
from katana.query.graph_projection import GraphProjection

# Create an event store
event_store = EventStore()

# Create a graph projection
graph_projection = GraphProjection(event_store)

# Build the projection
graph_projection.build()

# Get the graph
graph = graph_projection.get_graph()
```
