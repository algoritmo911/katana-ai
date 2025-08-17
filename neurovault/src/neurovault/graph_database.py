import os
from neo4j import GraphDatabase

# Get Neo4j connection details from environment variables
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


class GraphDBConnection:
    """
    Manages the connection to the Neo4j database.
    """

    def __init__(self, uri, user, password):
        self._driver = None
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            # In a real app, you might want to handle this more gracefully.
            # For now, we'll let it fail fast.
            raise

    def close(self):
        """Closes the database driver connection."""
        if self._driver is not None:
            self._driver.close()
            print("Neo4j connection closed.")

    def get_driver(self):
        """Returns the active Neo4j driver."""
        return self._driver


# Create a singleton instance of the connection to be used across the application.
graph_db_connection = GraphDBConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)


def get_graph_driver():
    """Provides access to the singleton Neo4j driver instance."""
    return graph_db_connection.get_driver()
