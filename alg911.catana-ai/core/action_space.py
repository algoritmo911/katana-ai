# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: ActionSpace
# ОПИСАНИЕ: Определяет набор возможных действий, которые агент может "пробовать"
# совершить в ходе симуляции будущего.
# =======================================================================================================================

from typing import List, Dict, Any

class ActionSpace:
    """
    Defines the discrete set of high-level actions available to the agent
    during the simulation phase of the Dream Engine.
    """
    def __init__(self):
        # In a more advanced system, this could be dynamically generated based
        # on the current world state. For now, it's a static list.
        self._actions: List[Dict[str, Any]] = [
            {
                "name": "wait",
                "description": "Do nothing and observe the passage of time.",
                "params": {"duration_hours": 1}
            },
            {
                "name": "expand_knowledge",
                "description": "Focus computational resources on expanding the knowledge graph about a specific topic.",
                "params": {"topic": "machine_learning_ethics"} # Example topic
            },
            {
                "name": "reduce_system_fatigue",
                "description": "Perform maintenance tasks like clearing caches and optimizing processes to reduce system fatigue.",
                "params": {}
            },
            {
                "name": "run_deep_diagnostics",
                "description": "Run a comprehensive diagnostic suite to get a more accurate picture of system health.",
                "params": {}
            }
        ]

    def get_possible_actions(self, world_state: Any = None) -> List[Dict[str, Any]]:
        """
        Returns the list of possible actions.

        The world_state parameter is included for future expansion, where the
        possible actions might depend on the current state of the world.

        :param world_state: The current WorldStateSnapshot (not used in this version).
        :return: A list of action dictionaries.
        """
        return self._actions

if __name__ == '__main__':
    # --- Test ---
    action_space = ActionSpace()
    actions = action_space.get_possible_actions()

    print("--- ActionSpace ---")
    print(f"Discovered {len(actions)} possible actions:")
    import json
    print(json.dumps(actions, indent=2))

    assert len(actions) > 0
    assert "name" in actions[0]
    print("\n--- ActionSpace Verified ---")
