import unittest

from katana.neurovault.mock_db import get_driver
from katana.somnium.incarnator import Incarnator

class TestIncarnator(unittest.TestCase):

    def setUp(self):
        driver = get_driver()
        self.incarnator = Incarnator(driver)

    def test_incarnate_memory(self):
        """Test the full incarnation process."""
        blueprint = self.incarnator.incarnate_memory("mem-123")

        # There are 7 properties in the mock graph, so 7 qudits
        self.assertEqual(len(blueprint.qudits), 7)
        # There are 7 property-to-property handshakes from the 5 relationships
        self.assertEqual(len(blueprint.handshakes), 7)

        qudit_map = {q.name: q for q in blueprint.qudits}

        # Test a property that exists
        person_a_mood = qudit_map["person_a_mood"]
        self.assertEqual(person_a_mood.initial_states["t_0"], "happy")

        # Test a property that is missing (Uncertainty Translation)
        person_b_mood = qudit_map["person_b_mood"]
        self.assertIsInstance(person_b_mood.initial_states["t_0"], list)
        self.assertIn("happy", person_b_mood.initial_states["t_0"])
        self.assertIn("sad", person_b_mood.initial_states["t_0"])

        # Test an entanglement
        handshake_found = False
        for h in blueprint.handshakes:
            if h.qudit1 == "person_a_mood" and h.qudit2 == "object_1_type":
                handshake_found = True
                break
        self.assertTrue(handshake_found, "Did not find expected entanglement between person_a_mood and object_1_type")


if __name__ == "__main__":
    unittest.main()
