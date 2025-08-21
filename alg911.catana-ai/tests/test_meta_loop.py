# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: Integration Test for the Full Meta-Cognitive Loop
# ОПИСАНИЕ: Этот тест проверяет полный цикл Telos: от восприятия мира до
# самостоятельной генерации цели.
# =======================================================================================================================

import unittest
import sys
import os

# Adjust path to import from the project's root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.world_modeler import WorldModeler
from core.neurovault import Neurovault
from core.diagnost import Diagnost
from core.cassandra import Cassandra
from core.dream_engine import DreamEngine
from core.action_space import ActionSpace
from core.simulation_matrix import SimulationMatrix
from core.value_judgement_engine import ValueJudgementEngine
from core.goal_generator import GoalGenerator

class TestMetaCognitiveLoop(unittest.TestCase):

    def setUp(self):
        """Set up all the components needed for the meta-loop."""
        # Phase 1 Components
        self.world_modeler = WorldModeler(Neurovault(), Diagnost(), Cassandra())

        # Phase 2 Components
        self.dream_engine = DreamEngine(ActionSpace(), SimulationMatrix())

        # Phase 3 Components
        self.vje = ValueJudgementEngine()

        # Phase 4 Components
        self.goal_generator = GoalGenerator()

    def test_full_end_to_end_goal_generation(self):
        """
        Tests the entire meta-cognitive cycle from world state to goal generation.
        """
        print("\n--- Testing Full Meta-Cognitive Loop ---")

        # 1. World Modeler creates a snapshot of reality.
        print("Step 1: WorldModeler creating snapshot...")
        initial_state = self.world_modeler.create_world_state_snapshot()
        self.assertIsNotNone(initial_state)
        print("  -> Snapshot created successfully.")

        # 2. Dream Engine generates a nebula of possible futures.
        print("Step 2: DreamEngine generating nebula...")
        nebula = self.dream_engine.generate_future_nebula(initial_state, depth=3, breadth=2)
        self.assertTrue(len(nebula) > 1, "Nebula should have more than just the root node.")
        print(f"  -> Nebula generated with {len(nebula)} nodes.")

        # 3. Value Judgement Engine evaluates the nebula.
        print("Step 3: ValueJudgementEngine creating landscape of desires...")
        landscape = self.vje.evaluate_nebula(nebula, initial_state)
        # Check that at least one node has a score
        scored_nodes = [node for node in landscape.values() if node.value_score is not None]
        self.assertTrue(len(scored_nodes) > 0)
        print("  -> Landscape evaluated successfully.")

        # 4. Goal Generator produces a high-level goal.
        print("Step 4: GoalGenerator producing a goal...")
        goal = self.goal_generator.generate_goal(landscape)
        self.assertIsNotNone(goal, "Goal Generator should have produced a goal.")
        self.assertIn("goal", goal)
        self.assertIn("priority", goal)
        self.assertIn("source", goal)
        self.assertEqual(goal["source"], "TelosGoalGenerator")
        print(f"  -> Goal Generated: {goal}")

        print("--- Full Meta-Cognitive Loop Verified ---")


if __name__ == '__main__':
    unittest.main()
