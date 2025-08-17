# 2. Choice of Graph Database: Neo4j

Date: 2025-08-16

## Status

Accepted

## Context

While a vector database answers the question "What is similar?", Project Mnemosyne also requires a system to answer "How is this related?". We need to store structured knowledge, representing entities (people, projects, technologies) and the explicit relationships between them. This structured knowledge graph is the second pillar of Katana's memory fabric.

The options considered were:
1.  **Native Graph Databases:** Systems like Neo4j or Memgraph that are specifically designed for storing and querying graph data.
2.  **RDF Stores:** Triple stores like Apache Jena or GraphDB that are based on W3C standards (RDF, SPARQL).
3.  **Simulating a Graph in a Relational Database:** Using tables to represent nodes and edges, which often leads to complex and inefficient queries.

## Decision

We have decided to use **Neo4j**.

This decision is based on the following rationale:
- **Labeled Property Graph (LPG) Model:** Neo4j's LPG model is intuitive and flexible. It allows nodes and relationships to have labels and properties, which is a natural fit for modeling real-world knowledge.
- **Cypher Query Language:** Cypher is a powerful, declarative query language specifically designed for graphs. Its ASCII-art-like syntax makes it highly readable and expressive for graph traversal and pattern matching.
- **Maturity and Community:** Neo4j is the most mature and widely adopted native graph database. It has a large community, extensive documentation, and excellent client library support in many languages, including Python.
- **Performance:** As a native graph database, its "index-free adjacency" allows for extremely fast traversal of relationships, which is much more efficient than the recursive joins required in a relational database.
- **Tooling and Ecosystem:** Neo4j comes with a rich ecosystem, including the Neo4j Browser for visualization and exploration, and APOC (Awesome Procedures on Cypher) for extended functionality.

## Consequences

- **Positive:**
    - Provides a powerful and explicit way to model complex relationships in our knowledge base.
    - Enables queries that are difficult or impossible with a vector or relational database alone (e.g., "Find all developers who worked on projects that use a specific technology").
    - The schema is flexible and can evolve easily as new types of entities and relationships are identified.
- **Negative:**
    - Introduces another database system into our stack, which adds to operational complexity. However, this is mitigated by using the official Docker container.
    - Requires learning the Cypher query language, though it is generally considered easier to learn than SPARQL.
