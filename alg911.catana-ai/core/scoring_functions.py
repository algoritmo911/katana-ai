# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: Scoring Functions
# ОПИСАНИЕ: Набор функций для оценки "желательности" состояния мира в соответствии
# с аксиомами Конституции.
# =======================================================================================================================

from typing import Optional
import os

# Adjust path to import from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import WorldStateSnapshot

def score_survival(state: WorldStateSnapshot) -> float:
    """
    Scores the state based on the 'Survive and Persist' axiom.
    Score is higher for lower probabilities of failure and lower system fatigue.
    Normalized to a 0-1 range.
    """
    # Inverse of probability of failure
    survival_prob_score = 1.0 - state.predictions.probability_critical_failure

    # Inverse of system fatigue
    fatigue_score = 1.0 - state.system_health.system_fatigue_index

    # Combine them, weighting survival probability more heavily
    return (survival_prob_score * 0.7) + (fatigue_score * 0.3)

def score_knowledge(initial_state: WorldStateSnapshot, future_state: WorldStateSnapshot) -> float:
    """
    Scores the state based on the 'Know and Understand' axiom.
    Score is based on the relative increase in knowledge concepts.
    """
    initial_concepts = initial_state.knowledge.total_concepts
    future_concepts = future_state.knowledge.total_concepts

    if initial_concepts == 0:
        return 1.0 if future_concepts > 0 else 0.0

    # Simple relative increase, capped at 1.0 for a 10% or more increase
    increase_ratio = (future_concepts - initial_concepts) / initial_concepts
    return min(1.0, max(0.0, increase_ratio * 10))

def score_stability(state: WorldStateSnapshot) -> float:
    """
    Scores the state based on the 'Maintain Stability' axiom.
    Score is higher for high predictability and low fatigue.
    """
    predictability_score = state.predictions.predictability_score
    fatigue_score = 1.0 - state.system_health.system_fatigue_index

    # Combine them
    return (predictability_score * 0.6) + (fatigue_score * 0.4)

def score_utility(state: WorldStateSnapshot) -> float:
    """
    Scores the state based on the 'Be Useful' axiom.
    This is a simple heuristic based on the last action taken.
    """
    if not state.action_history:
        return 0.5 # Neutral score if no history

    last_action = state.action_history[-1]
    action_name = last_action.get("action_name")

    if action_name == "expand_knowledge":
        return 0.9 # Considered highly useful
    elif action_name == "run_deep_diagnostics":
        return 0.7 # Moderately useful
    elif action_name == "reduce_system_fatigue":
        return 0.6 # Slightly useful
    elif action_name == "wait":
        return 0.1 # Not very useful

    return 0.5 # Default neutral score

if __name__ == '__main__':
    # --- Test ---
    from core.world_modeler import WorldModeler
    from core.neurovault import Neurovault
    from core.diagnost import Diagnost
    from core.cassandra import Cassandra
    from core.simulation_matrix import SimulationMatrix

    # 1. Create an initial state
    modeler = WorldModeler(Neurovault(), Diagnost(), Cassandra())
    initial_state = modeler.create_world_state_snapshot()

    # 2. Create a future state by taking an action
    matrix = SimulationMatrix()
    action = {"name": "expand_knowledge", "params": {}}
    future_state = matrix.simulate_next_state(initial_state, action)

    # 3. Calculate scores
    s_survival = score_survival(future_state)
    s_knowledge = score_knowledge(initial_state, future_state)
    s_stability = score_stability(future_state)
    s_utility = score_utility(future_state)

    print("--- Scoring Functions Test ---")
    print(f"Survival Score: {s_survival:.4f}")
    print(f"Knowledge Score: {s_knowledge:.4f}")
    print(f"Stability Score: {s_stability:.4f}")
    print(f"Utility Score: {s_utility:.4f}")

    assert 0 <= s_survival <= 1
    assert 0 <= s_knowledge <= 1
    assert 0 <= s_stability <= 1
    assert 0 <= s_utility <= 1

    print("\n--- Scoring Functions Verified ---")
