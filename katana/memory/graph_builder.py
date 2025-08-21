import logging
from typing import Dict, Any, Optional
from katana.memory.memory_fabric import MemoryFabric
from katana.utils.hash_utils import generate_chronohash

# Initialize logger
logger = logging.getLogger(__name__)

class GraphBuilder:
    """
    Translates high-level events into a graph structure of nodes and edges
    and uses MemoryFabric to persist them.
    """
    def __init__(self, memory_fabric: MemoryFabric):
        self.fabric = memory_fabric
        logger.info("GraphBuilder initialized.")

    def process_dialogue_event(self, dialogue_data: Dict[str, Any]):
        """
        Processes a dialogue event, creates the relevant nodes and edges,
        and persists them using the MemoryFabric.

        Args:
            dialogue_data: A dictionary containing the details of the dialogue event.
                           Expected keys: 'user_id', 'timestamp', 'command_name', etc.
        """
        if not self.fabric:
            logger.error("MemoryFabric not available. Cannot process dialogue event.")
            return

        user_id = dialogue_data.get("user_id")
        timestamp = dialogue_data.get("timestamp")
        logger.debug(f"Processing dialogue event for user: {user_id} at {timestamp}")

        # 1. Generate ChronoHash for the event
        temporal_source = "telegram_dialogue"
        event_id = f"{user_id}-{timestamp}" # A simple unique ID for this event
        try:
            chronos_id = generate_chronohash(temporal_source, event_id)
        except ValueError as e:
            logger.error(f"Could not generate ChronoHash for event: {e}", exc_info=True)
            return


        # 2. Create the main 'MemoryEvent' node
        event_attributes = {
            "command_name": dialogue_data.get("command_name"),
            "input": dialogue_data.get("input_data"),
            "output": dialogue_data.get("output_data"),
            "duration": dialogue_data.get("duration"),
            "success": dialogue_data.get("success"),
            "timestamp": timestamp,
            "temporal_source": temporal_source,
        }
        event_node = self.fabric.add_node(
            node_type="MemoryEvent",
            attributes=event_attributes,
            chronos_id=chronos_id
        )

        if not event_node:
            logger.error("Failed to create MemoryEvent node. Aborting graph build for this event.")
            return

        # 3. Create or retrieve the 'Author' node (the user)
        # In a real implementation, we would check if the user node already exists.
        # For now, we'll create a new one each time for simplicity.
        author_attributes = {"user_id": user_id}
        author_node = self.fabric.add_node(
            node_type="Author",
            attributes=author_attributes
        )

        if not author_node:
            logger.warning(f"Failed to create Author node for user: {user_id}")
            # We can still proceed without the author node, but we'll log it.
        else:
            # 4. Create an edge linking the Author to the MemoryEvent
            self.fabric.add_edge(
                source_node_id=author_node["id"],
                target_node_id=event_node["id"],
                edge_type="authored",
                attributes={"role": "user"}
            )

        logger.info(f"Successfully processed and built graph components for event from user {user_id} with ChronoHash: {chronos_id}")

        # Future steps:
        # - Extract entities from input/output and create 'Entity' nodes.
        # - Link this event to a 'LogicalFlow' or 'Narrative' node.
        # - Create 'happened_before' edges to link to previous events from the same user.
