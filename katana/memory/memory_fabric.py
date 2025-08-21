import logging
from typing import List, Dict, Any, Optional
from supabase import Client

# Initialize logger
logger = logging.getLogger(__name__)

class MemoryFabric:
    """
    A class to handle all interactions with the graph-based memory in Supabase.
    This class provides an interface for creating, retrieving, and managing nodes and edges.
    """
    def __init__(self, supabase_client: Optional[Client]):
        self.client = supabase_client
        if self.client:
            logger.info("MemoryFabric initialized with Supabase client.")
        else:
            logger.warning("MemoryFabric initialized without a Supabase client. Operations will be limited.")

    def add_node(self, node_type: str, attributes: Dict[str, Any], chronos_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Adds a new node to the 'nodes' table.

        Args:
            node_type: The type of the node (e.g., 'MemoryEvent', 'Entity').
            attributes: A dictionary of attributes for the node.
            chronos_id: An optional unique, deterministic hash for the node.

        Returns:
            The newly created node, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not available. Cannot add node.")
            return None

        node_entry = {
            "node_type": node_type,
            "attributes": attributes,
            "chronos_id": chronos_id
        }
        try:
            response = self.client.table("nodes").insert(node_entry).execute()
            # Simplified response handling for now
            if response.data:
                logger.debug(f"Successfully added node: {response.data[0]['id']}")
                return response.data[0]
            if response.error:
                 logger.error(f"Error adding node: {response.error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error adding node: {e}", exc_info=True)
            return None

    def add_edge(self, source_node_id: str, target_node_id: str, edge_type: str, weight: Optional[float] = None, attributes: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Adds a new edge to the 'edges' table.

        Args:
            source_node_id: The ID of the source node.
            target_node_id: The ID of the target node.
            edge_type: The type of the edge (e.g., 'happened_before', 'caused').
            weight: An optional weight for the edge.
            attributes: Optional metadata for the edge.

        Returns:
            The newly created edge, or None if an error occurred.
        """
        if not self.client:
            logger.error("Supabase client not available. Cannot add edge.")
            return None

        edge_entry = {
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "edge_type": edge_type,
            "weight": weight,
            "attributes": attributes
        }
        try:
            response = self.client.table("edges").insert(edge_entry).execute()
            # Simplified response handling
            if response.data:
                logger.debug(f"Successfully added edge between {source_node_id} and {target_node_id}")
                return response.data[0]
            if response.error:
                logger.error(f"Error adding edge: {response.error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error adding edge: {e}", exc_info=True)
            return None
