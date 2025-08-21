import unittest

from katana.neurovault.mock_db import get_driver
from katana.somnium.incarnator import Incarnator

import unittest
from unittest.mock import MagicMock

from katana.neurovault.mock_db import get_driver
from katana.somnium.incarnator import Incarnator
from katana.somnium.intervention_actuator import InterventionActuator
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator


class TestIncarnator(unittest.TestCase):

    def setUp(self):
        driver = get_driver()
        self.incarnator = Incarnator(driver)

    def test_incarnate_memory(self):
        """Test the full incarnation process."""
        blueprint = self.incarnator.incarnate_memory("mem-123")

        self.assertEqual(len(blueprint.qudits), 7)
        self.assertEqual(len(blueprint.handshakes), 2) # Based on the refined weaver logic

        qudit_map = {q.name: q for q in blueprint.qudits}

        # Test a property that exists
        person_a_mood = qudit_map["person_a_mood"]
        self.assertEqual(person_a_mood.initial_states["t_0"], "happy")

        # Test a property that is missing (Uncertainty Translation)
        person_b_mood = qudit_map["person_b_mood"]
        self.assertIsInstance(person_b_mood.initial_states["t_0"], list)
        self.assertIn("happy", person_b_mood.initial_states["t_0"])
        self.assertIn("sad", person_b_mood.initial_states["t_0"])

        # Test an entanglement based on the new primary property logic
        handshake_found = False
        for h in blueprint.handshakes:
            if h.qudit1 == "object_1_type" and h.qudit2 == "object_2_state":
                handshake_found = True
                break
        self.assertTrue(handshake_found, "Did not find expected entanglement between key and door")


class TestInterventionActuator(unittest.TestCase):

    def setUp(self):
        self.compiler = Compiler()
        self.simulator = QuantumStateSimulator()
        self.actuator = InterventionActuator(self.compiler, self.simulator)

        # Load a blueprint into the simulator to have a state to intervene on
        driver = get_driver()
        incarnator = Incarnator(driver)
        blueprint = incarnator.incarnate_memory("mem-123")
        circuit = self.compiler.compile(blueprint)
        self.compiler.run(circuit, self.simulator)

    def test_intervene(self):
        """Test that the actuator correctly applies an intervention."""
        # Check pre-condition
        initial_state = self.simulator.qudits["object_2_state"]["t_0"]
        self.assertEqual(initial_state, [("closed", 1.0)])

        # The intervention
        command = {"target": "object_2_state", "state": "open"}
        self.actuator.intervene(command)

        # Check post-condition
        final_state = self.simulator.qudits["object_2_state"]["t_0"]
        self.assertEqual(final_state, [("open", 1.0)])


if __name__ == "__main__":
    unittest.main()
