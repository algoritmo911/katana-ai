import logging
import yaml
from enum import Enum, auto
from pathlib import Path

import networkx as nx

from .events import GestaltEvent

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    VALID = auto()
    SUSPICIOUS = auto()
    INVALID = auto()

class Inquisitor:
    """
    The Inquisitor daemon, responsible for validating incoming events
    against the existing knowledge graph and a defined ontology.
    """
    def __init__(self, ontology_path: str = "katana/gestalt/ontology.yaml"):
        self.ontology = self._load_ontology(ontology_path)
        if not self.ontology:
            logger.error("Inquisitor initialized with no ontology. All validation checks will be skipped.")

    def _load_ontology(self, ontology_path: str):
        """Loads the system ontology from a YAML file."""
        try:
            path = Path(ontology_path)
            if not path.exists():
                logger.error(f"Ontology file not found at: {ontology_path}")
                return None
            with open(path, 'r') as f:
                ontology = yaml.safe_load(f)
            logger.info(f"Ontology loaded successfully from {ontology_path}")
            return ontology
        except Exception as e:
            logger.error(f"Failed to load or parse ontology file: {e}", exc_info=True)
            return None

    def validate(self, event: GestaltEvent, graph: nx.MultiDiGraph, entity_extractor) -> ValidationStatus:
        """
        Validates a new event against the graph and ontology.

        :param event: The GestaltEvent to validate.
        :param graph: The current knowledge graph.
        :param entity_extractor: The entity extractor to find entities in the event.
        :return: A ValidationStatus (VALID, SUSPICIOUS, or INVALID).
        """
        if not self.ontology:
            return ValidationStatus.VALID # Cannot validate without an ontology

        # For now, we only implement a simple contradiction check.
        # Ontological validation is a placeholder for future, more complex rules.
        return self._check_for_emotional_contradiction(event, graph, entity_extractor)

    def _check_for_emotional_contradiction(
        self, event: GestaltEvent, graph: nx.MultiDiGraph, entity_extractor,
        threshold: float = 0.7, recency_limit: int = 10
    ) -> ValidationStatus:
        """
        A simple contradiction check based on emotional valence.

        Flags an event as SUSPICIOUS if it's strongly negative about an entity
        that was recently involved in a strongly positive event.
        """
        if event.valence is None or not isinstance(event.content, str):
            return ValidationStatus.VALID

        # Check only for strongly negative events
        if event.valence > -threshold:
            return ValidationStatus.VALID

        entities = entity_extractor.extract_entities(event.content)
        if not entities:
            return ValidationStatus.VALID

        for entity in entities:
            if not graph.has_node(entity):
                continue

            # Look at recent events involving this entity
            # Predecessors of the entity node are events that contain it.
            # We need to traverse backwards from the most recent events in the graph.
            recent_event_nodes = [n for n, d in graph.nodes(data=True) if d.get('type') == 'Event']
            # Get the last N events
            for event_node_id in reversed(recent_event_nodes[-recency_limit:]):
                if graph.has_edge(event_node_id, entity):
                    # This event is linked to the entity. Check its valence.
                    past_event_valence = graph.nodes[event_node_id].get('valence')
                    if past_event_valence is not None and past_event_valence > threshold:
                        logger.warning(
                            f"SUSPICIOUS event {event.event_id}: Strong negative valence ({event.valence:.2f}) for entity '{entity}', "
                            f"which had a recent strong positive event ({past_event_valence:.2f}) "
                            f"in event {event_node_id}."
                        )
                        return ValidationStatus.SUSPICIOUS

        return ValidationStatus.VALID
