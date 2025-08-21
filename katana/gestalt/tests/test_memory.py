import unittest
import sys
from pathlib import Path
import uuid

# Adjust path to make katana modules importable
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from katana.gestalt.memory import GraphMemory
from katana.gestalt.events import GestaltEvent

class TestGraphMemory(unittest.TestCase):

    def setUp(self):
        """Set up a new GraphMemory instance for each test."""
        self.keywords = ['error', 'system']
        self.memory = GraphMemory(entity_keywords=self.keywords)

    def test_add_single_event(self):
        """Test adding a single event to the graph."""
        event = GestaltEvent(source_id="test_sensor", content="A system error occurred.")

        self.memory.add_event(event)

        # Assertions
        # Check that the event node was added
        self.assertTrue(self.memory.graph.has_node(event.event_id))
        node_data = self.memory.graph.nodes[event.event_id]
        self.assertEqual(node_data['type'], 'Event')
        self.assertEqual(node_data['content'], event.content)

        # Check that entity nodes were added
        self.assertTrue(self.memory.graph.has_node('system'))
        self.assertTrue(self.memory.graph.has_node('error'))

        # Check that edges were created
        self.assertTrue(self.memory.graph.has_edge(event.event_id, 'system'))
        self.assertTrue(self.memory.graph.has_edge(event.event_id, 'error'))

        # Check edge type
        edge_data = self.memory.graph.get_edge_data(event.event_id, 'system')[0]
        self.assertEqual(edge_data['type'], 'CONTAINS_ENTITY')

    def test_add_sequential_events(self):
        """Test that sequential events are correctly linked."""
        event1 = GestaltEvent(source_id="test_sensor", content="First event.")
        event2 = GestaltEvent(source_id="test_sensor", content="Second event with an error.")

        self.memory.add_event(event1)
        self.memory.add_event(event2)

        # Check for the sequential edge
        self.assertTrue(self.memory.graph.has_edge(event1.event_id, event2.event_id))
        edge_data = self.memory.graph.get_edge_data(event1.event_id, event2.event_id)[0]
        self.assertEqual(edge_data['type'], 'SEQUENTIAL')

        # Check that the last_event_id was updated
        self.assertEqual(self.memory.last_event_id, event2.event_id)

    def test_entity_nodes_are_reused(self):
        """Test that existing entity nodes are reused, not duplicated."""
        event1 = GestaltEvent(source_id="s1", content="A system error.")
        event2 = GestaltEvent(source_id="s2", content="Another system issue.")

        self.memory.add_event(event1)
        self.memory.add_event(event2)

        # Count how many nodes are of type 'Entity' with the name 'system'
        system_nodes = [n for n, d in self.memory.graph.nodes(data=True) if d.get('type') == 'Entity' and n == 'system']
        self.assertEqual(len(system_nodes), 1)

        # Check that both events link to the same entity node
        self.assertTrue(self.memory.graph.has_edge(event1.event_id, 'system'))
        self.assertTrue(self.memory.graph.has_edge(event2.event_id, 'system'))

if __name__ == '__main__':
    unittest.main()
