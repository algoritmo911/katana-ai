import unittest
import sys
from pathlib import Path
import networkx as nx

# Adjust path to make katana modules importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.gestalt.inquisitor import Inquisitor, ValidationStatus
from katana.gestalt.events import GestaltEvent
from katana.gestalt.nlp import EntityExtractor

class TestInquisitor(unittest.TestCase):

    def setUp(self):
        # A mock ontology path can be used if we create a test ontology file
        # For now, we rely on the default path.
        self.inquisitor = Inquisitor()
        self.entity_extractor = EntityExtractor(keywords=['database'])
        self.graph = nx.MultiDiGraph()

    def test_valid_event_passes(self):
        """Test that a normal, non-contradictory event is marked as VALID."""
        event = GestaltEvent(source_id="s1", content="Normal operation.", valence=0.1)
        status = self.inquisitor.validate(event, self.graph, self.entity_extractor)
        self.assertEqual(status, ValidationStatus.VALID)

    def test_contradiction_is_suspicious(self):
        """Test that a contradictory event is marked as SUSPICIOUS."""
        # Arrange: Add a strong positive event about the 'database' to the graph
        positive_event = GestaltEvent(
            source_id="s1",
            content="The database performance is amazing!",
            valence=0.8
        )
        # Manually add the node and entity to the graph for the test
        self.graph.add_node(positive_event.event_id, type='Event', valence=positive_event.valence)
        self.graph.add_node('database', type='Entity')
        self.graph.add_edge(positive_event.event_id, 'database', type='CONTAINS_ENTITY')

        # Act: A new, strongly negative event about the same entity arrives
        negative_event = GestaltEvent(
            source_id="s2",
            content="The database is a horrible failure.",
            valence=-0.8
        )
        status = self.inquisitor.validate(negative_event, self.graph, self.entity_extractor)

        # Assert
        self.assertEqual(status, ValidationStatus.SUSPICIOUS)

    def test_no_contradiction_if_not_recent(self):
        """Test that old positive events don't trigger suspicion."""
        # Arrange: Add the positive event first.
        positive_event = GestaltEvent(
            source_id="s1",
            content="The database performance is amazing!",
            valence=0.8
        )
        self.graph.add_node(positive_event.event_id, type='Event', valence=positive_event.valence)
        self.graph.add_node('database', type='Entity')
        self.graph.add_edge(positive_event.event_id, 'database', type='CONTAINS_ENTITY')

        # Arrange: Add 15 other events to push the positive one out of the recency window
        for i in range(15):
            ev = GestaltEvent(source_id="filler", content=f"filler event {i}")
            self.graph.add_node(ev.event_id, type='Event', valence=0.0)

        # Act
        negative_event = GestaltEvent(
            source_id="s2",
            content="The database is a horrible failure.",
            valence=-0.8
        )
        status = self.inquisitor.validate(negative_event, self.graph, self.entity_extractor)

        # Assert: The positive event is too old to be considered a contradiction
        self.assertEqual(status, ValidationStatus.VALID)

    def test_no_contradiction_if_valence_is_weak(self):
        """Test that weakly valenced events do not trigger suspicion."""
        # Positive event is not strong enough
        positive_event = GestaltEvent(source_id="s1", content="database is ok.", valence=0.4)
        self.graph.add_node(positive_event.event_id, type='Event', valence=positive_event.valence)
        self.graph.add_node('database', type='Entity')
        self.graph.add_edge(positive_event.event_id, 'database', type='CONTAINS_ENTITY')

        # Negative event is not strong enough
        negative_event = GestaltEvent(source_id="s2", content="database is slow.", valence=-0.4)
        status = self.inquisitor.validate(negative_event, self.graph, self.entity_extractor)
        self.assertEqual(status, ValidationStatus.VALID)


if __name__ == '__main__':
    unittest.main()
