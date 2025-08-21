# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: SimulationMatrix
# ОПИСАНИЕ: "Физический движок" для симуляции. Принимает состояние мира и действие,
# и вычисляет следующее состояние мира. Это — реализация "Протокола Хронос".
# =======================================================================================================================

import copy
import datetime
import random
from typing import Dict, Any
import os

# Adjust path to import from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import WorldStateSnapshot

class SimulationMatrix:
    """
    The Simulation Matrix acts as the "physics engine" for the Dream Engine.
    It takes a world state and an action, and computes the resultant next state.
    """

    def simulate_next_state(self, current_state: WorldStateSnapshot, action: Dict[str, Any]) -> WorldStateSnapshot:
        """
        Calculates the next WorldStateSnapshot based on a given state and action.

        :param current_state: The starting WorldStateSnapshot.
        :param action: The action to perform.
        :return: A new WorldStateSnapshot representing the future state.
        """
        # Start with a deep copy of the current state to avoid mutation
        next_state = copy.deepcopy(current_state)

        # Update timestamp
        duration_hours = action.get("params", {}).get("duration_hours", 1)
        current_time = datetime.datetime.fromisoformat(next_state.timestamp)
        next_time = current_time + datetime.timedelta(hours=duration_hours)
        next_state.timestamp = next_time.isoformat()

        # Update action history
        next_state.action_history.append({
            "action_name": action["name"],
            "params": action.get("params", {}),
            "simulated_at": next_state.timestamp
        })
        # Keep history from getting too long
        if len(next_state.action_history) > 10:
            next_state.action_history.pop(0)

        # Apply state changes based on the action
        action_name = action.get("name")

        # --- Default time-based state evolution ---
        # System fatigue naturally changes based on the predicted trend
        fatigue_change = next_state.predictions.system_fatigue_trend * duration_hours
        next_state.system_health.system_fatigue_index += fatigue_change

        if action_name == "expand_knowledge":
            # Increases knowledge but also fatigue
            next_state.knowledge.total_concepts += random.randint(5, 20)
            next_state.knowledge.total_relationships += random.randint(10, 40)
            next_state.system_health.system_fatigue_index += 0.05

        elif action_name == "reduce_system_fatigue":
            # Reduces fatigue significantly
            next_state.system_health.system_fatigue_index *= 0.5

        elif action_name == "run_deep_diagnostics":
            # Improves self-knowledge and predictability
            next_state.knowledge.consistency = min(1.0, next_state.knowledge.consistency + 0.02)
            next_state.predictions.predictability_score = min(1.0, next_state.predictions.predictability_score + 0.05)

        # Clamp values to reasonable bounds
        next_state.system_health.system_fatigue_index = max(0.0, min(1.0, next_state.system_health.system_fatigue_index))

        return next_state

if __name__ == '__main__':
    # --- Test ---
    from core.world_modeler import WorldModeler
    from core.neurovault import Neurovault
    from core.diagnost import Diagnost
    from core.cassandra import Cassandra

    # 1. Create an initial state
    modeler = WorldModeler(Neurovault(), Diagnost(), Cassandra())
    initial_state = modeler.create_world_state_snapshot()
    print("--- SimulationMatrix Test ---")
    print("Initial State Fatigue:", initial_state.system_health.system_fatigue_index)
    print("Initial State Concepts:", initial_state.knowledge.total_concepts)

    # 2. Define an action
    action_to_take = {
        "name": "expand_knowledge",
        "params": {"topic": "test_topic"}
    }

    # 3. Simulate the next state
    matrix = SimulationMatrix()
    next_state = matrix.simulate_next_state(initial_state, action_to_take)
    print("\nAction Taken:", action_to_take["name"])
    print("Next State Fatigue:", next_state.system_health.system_fatigue_index)
    print("Next State Concepts:", next_state.knowledge.total_concepts)

    assert next_state.system_health.system_fatigue_index > initial_state.system_health.system_fatigue_index
    assert next_state.knowledge.total_concepts > initial_state.knowledge.total_concepts
    assert len(next_state.action_history) == len(initial_state.action_history) + 1

    print("\n--- SimulationMatrix Verified ---")
