# 1. Choice of Vector Database: PostgreSQL with pgvector

Date: 2025-08-16

## Status

Accepted

## Context

Project Mnemosyne requires a persistent, reliable, and scalable database for storing and querying high-dimensional vector embeddings. This is the core of the Retrieval-Augmented Generation (RAG) system's memory. The choice of this database is critical for the performance and maintainability of the `neurovault` service.

Several options were considered:
1.  **Specialized Vector Databases:** Systems like Pinecone, Weaviate, or Milvus are purpose-built for vector search and offer high performance and advanced features.
2.  **General-Purpose Databases with Vector Extensions:** Traditional databases like PostgreSQL, enhanced with extensions like `pgvector`.
3.  **Search Libraries on a Filesystem:** Using libraries like FAISS directly on disk, which offers high performance but lacks database management features.

## Decision

We have decided to use **PostgreSQL with the `pgvector` extension**.

This decision is based on the following rationale:
- **Maturity and Reliability:** PostgreSQL is a battle-tested, open-source relational database with decades of development, a large community, and a strong reputation for data integrity.
- **Operational Simplicity:** By using a database we are likely already familiar with, we reduce the operational overhead of learning, deploying, and maintaining a completely new database system. It fits seamlessly into our existing Docker-based infrastructure.
- **Unified Data Model:** It allows us to store both the vector embeddings and their associated metadata (e.g., `text_chunk`, `source_document_id`) in the same relational table. This simplifies data management and avoids synchronization issues between a vector store and a separate metadata store.
- **Sufficient Performance:** For the scale of a personal AI co-pilot, `pgvector`'s performance is more than adequate. It supports exact and approximate nearest neighbor search with HNSW indexing, which is the industry standard.
- **Rich Ecosystem:** We can leverage the full power of PostgreSQL's ecosystem, including its advanced querying capabilities, backup and recovery tools (like `pg_dump`), and extensive client library support.

## Consequences

- **Positive:**
    - Reduced architectural complexity.
    - Simplified development and deployment pipeline.
    - Easy integration with standard ORMs like SQLAlchemy.
    - Data consistency is easier to maintain.
- **Negative:**
    - May not scale to the level of a dedicated, distributed vector database for applications with billions of embeddings, but this is not a requirement for Katana.
    - We are responsible for managing the PostgreSQL instance, though Docker simplifies this significantly.
