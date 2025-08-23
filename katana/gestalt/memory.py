import logging
from collections import deque
import networkx as nx
from .events import GestaltEvent
from .nlp import EntityExtractor

logger = logging.getLogger(__name__)


class GraphMemory:
    """
    A graph-based memory store for events and their relationships.
    """
    def __init__(self, entity_keywords: list[str] | None = None):
        self.graph = nx.MultiDiGraph()
        self.entity_extractor = EntityExtractor(keywords=entity_keywords or [])
        self.last_event_id = None
        logger.info("GraphMemory initialized.")

    def add_event(self, event: GestaltEvent):
        """
        Adds a new event to the graph memory, creating nodes and edges.
        """
        if not isinstance(event, GestaltEvent):
            logger.warning(f"Attempted to add non-GestaltEvent to GraphMemory. Type: {type(event)}. Skipping.")
            return

        # 1. Add the event node with all its data as attributes.
        # This is the "Temporal Weaver" action: stamping the event with time and confidence.
        event_id = event.event_id
        self.graph.add_node(
            event_id,
            type='Event',
            **event.model_dump()
        )
        logger.debug(f"Added Event node {event_id} to graph.")

        # 2. Add sequential edge, now with a timestamp.
        if self.last_event_id:
            self.graph.add_edge(
                self.last_event_id,
                event_id,
                type='SEQUENTIAL',
                timestamp=event.timestamp,
                confidence_score=1.0 # The sequence itself is a confident fact
            )
            logger.debug(f"Added SEQUENTIAL edge from {self.last_event_id} to {event_id}.")
        self.last_event_id = event_id

        # 3. Extract and link entities
        if isinstance(event.content, str):
            entities = self.entity_extractor.extract_entities(event.content)
            for entity_name in entities:
                # Add or update the entity node
                if not self.graph.has_node(entity_name):
                    self.graph.add_node(entity_name, type='Entity', first_seen=event.timestamp)
                    logger.debug(f"Added new Entity node '{entity_name}' to graph.")

                # Update last_seen timestamp for the entity
                self.graph.nodes[entity_name]['last_seen'] = event.timestamp

                # Add edge from event to entity
                self.graph.add_edge(
                    event_id,
                    entity_name,
                    type='CONTAINS_ENTITY',
                    timestamp=event.timestamp,
                    confidence_score=event.confidence_score # The link has same confidence as the event
                )
                logger.debug(f"Added CONTAINS_ENTITY edge from {event_id} to '{entity_name}'.")

    def get_event(self, event_id):
        """Retrieves an event node's data from the graph."""
        if self.graph.has_node(event_id):
            return self.graph.nodes[event_id]
        return None

    def __len__(self):
        # A simple measure of size could be the number of nodes.
        return self.graph.number_of_nodes()


class ShortTermMemory:
    """
    A simple in-memory store for recent events, using a capped collection.
    This serves as the short-term, working memory of the Gestalt engine.
    """

    def __init__(self, max_size: int = 1000):
        """
        Initializes the short-term memory.

        :param max_size: The maximum number of events to hold in memory.
                         Once the limit is reached, older events are discarded.
        """
        if max_size <= 0:
            raise ValueError("max_size must be a positive integer.")

        self.max_size = max_size
        self.events = deque(maxlen=max_size)
        logger.info(f"ShortTermMemory initialized with a max size of {max_size} events.")

    def add_event(self, event: GestaltEvent):
        """
        Adds a new event to the memory.
        If the memory is full, the oldest event is automatically discarded.
        """
        if not isinstance(event, GestaltEvent):
            logger.warning(f"Attempted to add non-GestaltEvent to memory. Type: {type(event)}. Skipping.")
            return

        self.events.append(event)
        logger.debug(f"Added event {event.event_id} to short-term memory.")

    def get_recent_events(self, count: int = 10) -> list[GestaltEvent]:
        """
        Retrieves a list of the most recent events.

        :param count: The number of recent events to retrieve.
        :return: A list of GestaltEvent objects.
        """
        if count <= 0:
            return []

        # The deque is ordered from oldest to newest, so we take from the right.
        # Slicing a deque is not as efficient as list slicing, but for retrieving
        # a small number of recent items, this is acceptable.
        # We can convert to a list and then slice.
        return list(self.events)[-count:]

    def get_all_events(self) -> list[GestaltEvent]:
        """
        Returns a copy of all events currently in memory.
        """
        return list(self.events)

    def __len__(self):
        return len(self.events)
