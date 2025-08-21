import unittest
from unittest.mock import patch

from katana.gallifreyan.ast import (
    SimulationBlueprint,
    TemporalQuditDeclaration,
    Objective,
    GateApplication,
    Measurement,
    HandshakeDeclaration,
    InterventionGate,
)
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator

class TestQuantumStateSimulator(unittest.TestCase):

    def setUp(self):
        self.simulator = QuantumStateSimulator()
        # A simple blueprint for testing
        self.blueprint = SimulationBlueprint(
            name="TestSim",
            reality_source="test",
            objective=Objective(name="TestObjective"),
            qudits=[
                TemporalQuditDeclaration(
                    name="Q1",
                    initial_states={"t_0": "A"}
                ),
                TemporalQuditDeclaration(
                    name="Q2",
                    initial_states={"t_0": ["X", "Y"]}
                )
            ]
        )
        self.simulator.load_blueprint(self.blueprint)

    def test_load_blueprint(self):
        self.assertIn("Q1", self.simulator.qudits)
        self.assertIn("Q2", self.simulator.qudits)
        # Check that single states are correctly converted to probabilistic form
        self.assertEqual(self.simulator.qudits["Q1"]["t_0"], [("A", 1.0)])
        # Check that superpositions are assigned equal probability
        self.assertEqual(self.simulator.qudits["Q2"]["t_0"], [("X", 0.5), ("Y", 0.5)])

    def test_apply_tardis_gate(self):
        gate_op = GateApplication(gate_name="TARDIS_Gate", target_qudit="Q1")
        self.simulator.execute_gate(gate_op)
        self.assertIn("t_0_next", self.simulator.qudits["Q1"])
        next_state = self.simulator.qudits["Q1"]["t_0_next"]
        self.assertEqual(len(next_state), 2)
        self.assertAlmostEqual(next_state[0][1], 0.5)
        self.assertAlmostEqual(next_state[1][1], 0.5)
        self.assertEqual(next_state[0][0], "A_outcome_A")

    @patch('random.choices')
    def test_execute_measurement(self, mock_choices):
        # Mock random.choices to always return the first state
        mock_choices.return_value = ["X"]

        measurement_op = Measurement(target_qudit="Q2")
        result = self.simulator.execute_measurement(measurement_op)

        self.assertEqual(result, "X")
        # Check that the wave function has collapsed
        self.assertEqual(self.simulator.qudits["Q2"]["t_0"], [("X", 1.0)])

    def test_measurement_shockwave(self):
        """Tests that measuring one qudit collapses an entangled one."""
        # Setup: Q_A is collapsed, Q_B is in superposition
        # They are entangled.
        self.blueprint.qudits = [
            TemporalQuditDeclaration(name="Q_A", initial_states={"t_0": "A"}),
            TemporalQuditDeclaration(name="Q_B", initial_states={"t_0": ["B1", "B2"]})
        ]
        self.blueprint.handshakes = [HandshakeDeclaration(qudit1="Q_A", qudit2="Q_B")]
        self.simulator.load_blueprint(self.blueprint)

        # Pre-condition check: Q_B is in superposition
        self.assertEqual(len(self.simulator.qudits["Q_B"]["t_0"]), 2)

        # Action: Measure Q_A
        measurement_op = Measurement(target_qudit="Q_A")
        self.simulator.execute_measurement(measurement_op)

        # Post-condition check: Q_B should now be collapsed due to entanglement
        self.assertEqual(len(self.simulator.qudits["Q_B"]["t_0"]), 1)
        self.assertEqual(self.simulator.qudits["Q_B"]["t_0"][0][1], 1.0) # Probability is 1.0
        self.assertEqual(self.simulator.qudits["Q_B"]["t_0"][0][0], "entangled_from(Q_A=A)")

    def test_execute_intervention(self):
        """Tests that an intervention forces a state and causes a shockwave."""
        self.blueprint.qudits = [
            TemporalQuditDeclaration(name="Q_A", initial_states={"t_0": "A"}),
            TemporalQuditDeclaration(name="Q_B", initial_states={"t_0": ["B1", "B2"]})
        ]
        self.blueprint.handshakes = [HandshakeDeclaration(qudit1="Q_A", qudit2="Q_B")]
        self.simulator.load_blueprint(self.blueprint)

        # Action: Intervene on Q_A
        intervention_op = InterventionGate(target_qudit="Q_A", force_state_to="Z")
        self.simulator.execute_intervention(intervention_op)

        # Post-condition check: Q_A is forced to Z
        self.assertEqual(self.simulator.qudits["Q_A"]["t_0"], [("Z", 1.0)])
        # Post-condition check: Entangled qudit Q_B is also collapsed
        self.assertEqual(len(self.simulator.qudits["Q_B"]["t_0"]), 1)
        self.assertEqual(self.simulator.qudits["Q_B"]["t_0"][0][0], "entangled_from(Q_A=Z)")


class TestCompiler(unittest.TestCase):

    def test_compile(self):
        compiler = Compiler()
        blueprint = SimulationBlueprint(
            name="CompileTest",
            reality_source="test",
            objective=Objective(
                name="CompileObjective",
                operations=[
                    GateApplication(gate_name="TARDIS_Gate", target_qudit="Q1"),
                    InterventionGate(target_qudit="Q2", force_state_to="Z"),
                    Measurement(target_qudit="Q1")
                ]
            )
        )
        circuit = compiler.compile(blueprint)
        self.assertEqual(len(circuit), 4)
        self.assertEqual(circuit[0][0], "load_blueprint")
        self.assertEqual(circuit[1][0], "execute_gate")
        self.assertEqual(circuit[2][0], "execute_intervention")
        self.assertEqual(circuit[3][0], "execute_measurement")
        self.assertIsInstance(circuit[2][1], InterventionGate)

if __name__ == "__main__":
    unittest.main()
