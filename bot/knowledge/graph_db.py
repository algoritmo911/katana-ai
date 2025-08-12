import os
from neo4j import GraphDatabase

class KnowledgeGraph:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def _execute_query(self, query, parameters=None):
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def add_triple(self, subject, verb, obj):
        """
        Adds a triple (subject, verb, object) to the graph.
        Example: (Jules, WORKS_ON, ProjectKuznitsa)
        """
        # Use MERGE to avoid creating duplicate nodes
        # Use MERGE on relationships to avoid creating duplicate relationships
        query = (
            "MERGE (s:%s {name: $s_name}) "
            "MERGE (o:%s {name: $o_name}) "
            "MERGE (s)-[r:%s]->(o)"
        ) % (subject['type'], obj['type'], verb)

        parameters = {
            "s_name": subject['name'],
            "o_name": obj['name']
        }

        self._execute_query(query, parameters)
        print(f"Added to graph: ({subject['name']})-[{verb}]->({obj['name']})")


# --- Singleton instance ---
_graph_instance = None

def get_graph_db():
    """
    Returns a singleton instance of the KnowledgeGraph.
    """
    global _graph_instance
    if _graph_instance is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password1234")
        _graph_instance = KnowledgeGraph(uri, user, password)
    return _graph_instance

def close_graph_db():
    """
    Closes the connection to the graph database.
    """
    global _graph_instance
    if _graph_instance is not None:
        _graph_instance.close()
        _graph_instance = None
