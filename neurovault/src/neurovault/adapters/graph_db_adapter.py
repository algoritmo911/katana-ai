from neo4j import Driver


class GraphDBAdapter:
    """
    Adapter for all interactions with the graph database (Neo4j).
    """

    def __init__(self, driver: Driver):
        if driver is None:
            raise ValueError("Neo4j driver is not initialized.")
        self.driver = driver

    def close(self):
        """Closes the connection to the database."""
        self.driver.close()

    def add_document(self, document_id: str, metadata: dict = None):
        """
        Adds a Document node to the graph if it doesn't already exist.
        This operation is idempotent.

        Args:
            document_id: A unique identifier for the document (e.g., file path).
            metadata: An optional dictionary of properties for the document node.
        """
        with self.driver.session() as session:
            session.execute_write(
                self._create_document_node, document_id, metadata or {}
            )

    @staticmethod
    def _create_document_node(tx, document_id, metadata):
        # Using MERGE ensures that we don't create duplicate nodes for the same document_id.
        # ON CREATE SET is executed only if the node is newly created.
        query = (
            "MERGE (d:Document {id: $document_id}) "
            "ON CREATE SET d += $metadata, d.created_at = timestamp() "
            "RETURN d"
        )
        tx.run(query, document_id=document_id, metadata=metadata)

    def add_entity(self, document_id: str, entity_name: str, entity_type: str):
        """
        Adds an Entity node and connects it to a Document node.
        This operation is idempotent.

        Args:
            document_id: The ID of the source document.
            entity_name: The name of the entity (e.g., "OpenAI", "Jules").
            entity_type: The type of the entity (e.g., "Organization", "Person").
        """
        with self.driver.session() as session:
            session.execute_write(
                self._create_entity_and_link, document_id, entity_name, entity_type
            )

    @staticmethod
    def _create_entity_and_link(tx, document_id, entity_name, entity_type):
        # This query does three things idempotently:
        # 1. Finds the Document node.
        # 2. Merges an Entity node (unique by name and type).
        # 3. Merges the relationship between them.
        query = (
            "MATCH (d:Document {id: $document_id}) "
            "MERGE (e:Entity {name: $entity_name, type: $entity_type}) "
            "MERGE (d)-[:CONTAINS_ENTITY]->(e)"
        )
        tx.run(query, document_id=document_id, entity_name=entity_name, entity_type=entity_type)

    def get_document_entities(self, document_id: str) -> list[dict]:
        """
        Retrieves all entities associated with a given document.
        """
        with self.driver.session() as session:
            result = session.execute_read(self._find_document_entities, document_id)
            return result

    @staticmethod
    def _find_document_entities(tx, document_id):
        query = (
            "MATCH (d:Document {id: $document_id})-[:CONTAINS_ENTITY]->(e:Entity) "
            "RETURN e.name AS name, e.type AS type"
        )
        records = tx.run(query, document_id=document_id)
        return [record.data() for record in records]
