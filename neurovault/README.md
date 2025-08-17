# NeuroVault - The Living Memory Fabric

This repository contains the **NeuroVault**, Katana's long-term memory and knowledge factory. It has been upgraded as part of **Project Mnemosyne** from a simulation to a persistent, industrial-grade memory system.

NeuroVault is responsible for the entire lifecycle of knowledge: Ingestion, Persistence, Retrieval, and Synthesis support.

## Architecture

NeuroVault is built on a dual-database model, running as a containerized service orchestrated by Docker Compose.

1.  **Vector Store (PostgreSQL + pgvector):**
    -   **Purpose:** Stores high-dimensional vector embeddings of text chunks for fast, semantic similarity search. This is the foundation of the RAG pipeline's retrieval capability.
    -   **Schema:** The `vector_embeddings` table stores the text chunk, a reference to its source document, and the vector itself.
    -   **Technology:** PostgreSQL 16 with the `pgvector` extension.

2.  **Graph Store (Neo4j):**
    -   **Purpose:** Stores structured knowledge by representing entities (e.g., people, projects) as nodes and their relationships as edges. This allows for complex queries about how information is connected.
    -   **Ontology:** The graph uses `Document`, `Entity`, and `Concept` nodes, connected by relationships like `CONTAINS_ENTITY`.
    -   **Technology:** Neo4j 5 with the Cypher query language.

3.  **API Server (`api_server.py`):**
    -   **Purpose:** Exposes NeuroVault's capabilities to other services (like `katana-ai`) via a simple REST API.
    -   **Endpoints:**
        -   `/retrieve`: Accepts a query and returns relevant context from the RAG pipeline.
        -   `/metrics`: Exposes Prometheus metrics for monitoring.

## Key Components

-   **`pipelines/ingestion.py`:** Contains the `IngestionOrchestrator` which reads documents from a source, processes them, and saves them to the databases.
-   **`pipelines/retrieval.py`:** Contains the `RAGQueryService` which powers the retrieval functionality.
-   **`adapters/`:** Contains the `VectorDBAdapter` and `GraphDBAdapter` which encapsulate all database-specific logic.
-   **`processing/`:** Contains the `TextProcessor` and `EmbeddingGenerator`.

## How to Use

The entire NeuroVault service, along with its databases, is managed by the `docker-compose.yml` file in the project root.

1.  **Start the Services:**
    ```bash
    docker-compose up --build neurovault
    ```

2.  **Initialize the Databases:**
    Before first use, you need to initialize the database schemas. You can do this by executing the init scripts inside the running container.
    ```bash
    # For the vector database
    docker-compose exec neurovault python init_db.py

    # To test the graph database connection
    docker-compose exec neurovault python test_graph_db.py
    ```

3.  **Run the Ingestion Pipeline:**
    To populate the databases with knowledge, run the ingestion pipeline, pointing it to the source material.
    ```bash
    docker-compose exec neurovault python run_ingestion.py
    ```
This will scan the `sapiens_notes_private` directory and ingest any `.md` files found.
