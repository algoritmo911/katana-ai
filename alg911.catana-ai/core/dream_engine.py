# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: The Dream Engine (Движок Сновидений)
# ОПИСАНИЕ: Исследует пространство возможностей, запуская симуляции будущего.
# =======================================================================================================================

import uuid
import random
from typing import Dict, List
import os

# Adjust path to import from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import WorldStateSnapshot, PossibleFutureNode
from core.simulation_matrix import SimulationMatrix
from core.action_space import ActionSpace

class DreamEngine:
    """
    The Dream Engine explores the space of possibilities by simulating future
    event chains based on a starting state.
    """
    def __init__(self, action_space: ActionSpace, simulation_matrix: SimulationMatrix):
        self.action_space = action_space
        self.simulation_matrix = simulation_matrix
        self.nebula_graph: Dict[str, PossibleFutureNode] = {}

    def generate_future_nebula(self, initial_state: WorldStateSnapshot, depth: int, breadth: int) -> Dict[str, PossibleFutureNode]:
        """
        Generates a graph of possible futures (the "Nebula").

        :param initial_state: The starting WorldStateSnapshot from the WorldModeler.
        :param depth: How many steps into the future to simulate.
        :param breadth: How many different actions to try at each step.
        :return: A dictionary representing the graph of possible futures.
        """
        self.nebula_graph = {}

        # Create the root node of the simulation tree
        root_node_id = str(uuid.uuid4())
        root_node = PossibleFutureNode(
            node_id=root_node_id,
            state=initial_state,
            depth=0
        )
        self.nebula_graph[root_node_id] = root_node

        self._dream_recursive(root_node, depth, breadth)

        return self.nebula_graph

    def _dream_recursive(self, current_node: PossibleFutureNode, remaining_depth: int, breadth: int):
        """
        A recursive helper function to build the simulation tree.
        This is a simplified tree search, not a full MCTS yet.
        """
        if remaining_depth <= 0:
            return

        possible_actions = self.action_space.get_possible_actions()

        # Limit the number of actions explored at each step to 'breadth'
        actions_to_try = random.sample(possible_actions, min(breadth, len(possible_actions)))

        for action in actions_to_try:
            # Use the simulation matrix to get the next state
            next_state = self.simulation_matrix.simulate_next_state(current_node.state, action)

            # Create the new node in the future graph
            child_node_id = str(uuid.uuid4())
            child_node = PossibleFutureNode(
                node_id=child_node_id,
                parent_id=current_node.node_id,
                state=next_state,
                action_taken=action,
                depth=current_node.depth + 1
            )

            # Add the new node to the graph and link it to the parent
            self.nebula_graph[child_node_id] = child_node
            current_node.children_ids.append(child_node_id)

            # Recurse deeper into the future
            self._dream_recursive(child_node, remaining_depth - 1, breadth)

if __name__ == '__main__':
    # --- Test ---
    from core.world_modeler import WorldModeler
    from core.neurovault import Neurovault
    from core.diagnost import Diagnost
    from core.cassandra import Cassandra

    # 1. Setup all necessary components
    action_space = ActionSpace()
    sim_matrix = SimulationMatrix()
    world_modeler = WorldModeler(Neurovault(), Diagnost(), Cassandra())

    # 2. Create an initial state
    initial_world_state = world_modeler.create_world_state_snapshot()

    # 3. Initialize and run the Dream Engine
    dream_engine = DreamEngine(action_space, sim_matrix)
    print("--- DreamEngine Test ---")
    print(f"Generating future nebula with depth=2, breadth=2...")

    nebula = dream_engine.generate_future_nebula(initial_world_state, depth=2, breadth=2)

    print(f"Generated a nebula with {len(nebula)} nodes.")

    # 4. Verification
    root_node = next(iter(nebula.values()))
    assert root_node.depth == 0
    assert len(root_node.children_ids) <= 2

    if root_node.children_ids:
        child_id = root_node.children_ids[0]
        child_node = nebula[child_id]
        assert child_node.depth == 1
        assert child_node.parent_id == root_node.node_id

        if child_node.children_ids:
            grandchild_id = child_node.children_ids[0]
            grandchild_node = nebula[grandchild_id]
            assert grandchild_node.depth == 2

    print("\n--- DreamEngine Verified ---")
    # For a more detailed view:
    # import json
    # print(json.dumps([node.model_dump() for node in nebula.values()], indent=2, default=str))
