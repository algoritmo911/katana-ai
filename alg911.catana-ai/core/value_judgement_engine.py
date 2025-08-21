# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: The Value Judgement Engine (Моральный Компас)
# ОПИСАНИЕ: Оценивает каждое возможное будущее на соответствие 'Конституции'.
# =======================================================================================================================

from typing import Dict, Optional
import os

# Adjust path to import from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import PossibleFutureNode, WorldStateSnapshot
from core import scoring_functions

class ValueJudgementEngine:
    """
    The Value Judgement Engine (or "Moral Compass") evaluates possible futures
    based on the agent's Constitution.
    """
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initializes the engine with weights for each constitutional axiom.
        These weights define the agent's "personality" and priorities.
        """
        if weights:
            self.weights = weights
        else:
            # Default weights, emphasizing survival and utility.
            self.weights = {
                "survival": 0.4,
                "knowledge": 0.15,
                "stability": 0.15,
                "utility": 0.3,
            }

        # Normalize weights to ensure they sum to 1
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

    def evaluate_nebula(self, nebula: Dict[str, PossibleFutureNode], initial_state: WorldStateSnapshot) -> Dict[str, PossibleFutureNode]:
        """
        Iterates through the Nebula graph and assigns a value score to each node.

        :param nebula: The graph of possible futures from the DreamEngine.
        :param initial_state: The starting state of the simulation, for comparison.
        :return: The same nebula graph, with the `value_score` populated on each node.
        """
        for node_id, node in nebula.items():
            # Calculate the score for each axiom
            s_survival = scoring_functions.score_survival(node.state)
            s_knowledge = scoring_functions.score_knowledge(initial_state, node.state)
            s_stability = scoring_functions.score_stability(node.state)
            s_utility = scoring_functions.score_utility(node.state)

            # Calculate the final weighted score
            weighted_score = (
                s_survival * self.weights["survival"] +
                s_knowledge * self.weights["knowledge"] +
                s_stability * self.weights["stability"] +
                s_utility * self.weights["utility"]
            )

            # Assign the score to the node
            node.value_score = weighted_score

        return nebula

if __name__ == '__main__':
    # --- Test ---
    from core.world_modeler import WorldModeler
    from core.neurovault import Neurovault
    from core.diagnost import Diagnost
    from core.cassandra import Cassandra
    from core.dream_engine import DreamEngine
    from core.action_space import ActionSpace
    from core.simulation_matrix import SimulationMatrix

    # 1. Generate a nebula of futures
    dream_engine = DreamEngine(ActionSpace(), SimulationMatrix())
    modeler = WorldModeler(Neurovault(), Diagnost(), Cassandra())
    initial_state = modeler.create_world_state_snapshot()
    nebula = dream_engine.generate_future_nebula(initial_state, depth=2, breadth=2)

    # 2. Evaluate the nebula
    vje = ValueJudgementEngine()
    scored_nebula = vje.evaluate_nebula(nebula, initial_state)

    print("--- ValueJudgementEngine Test ---")
    print(f"Evaluated {len(scored_nebula)} nodes in the nebula.")

    # 3. Verification
    for node in scored_nebula.values():
        print(f"  Node {node.node_id[:8]} (Depth {node.depth}): Value Score = {node.value_score:.4f}")
        assert node.value_score is not None
        assert 0 <= node.value_score <= 1

    print("\n--- ValueJudgementEngine Verified ---")
