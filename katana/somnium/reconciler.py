# -*- coding: utf-8 -*-
"""
The Reconciler Daemon.

This daemon reads the final, collapsed state of a simulation and reconciles
it with the Neurovault, creating a new, parallel timeline to record the
history of the altered reality.
"""
import uuid
from katana.neurovault.mock_db import MockNeurovaultDriver

class Reconciler:
    """
    Implements the Timeline Forking Protocol to save altered realities.
    """

    def __init__(self, driver: MockNeurovaultDriver):
        self._driver = driver

    def reconcile(self, original_memory_id: str, final_qudit_states: dict, intervention_log: list):
        """
        Analyzes the final state of a simulation and saves it as a new
        timeline in the Neurovault.
        """
        # --- 1. Generate IDs for the new reality ---
        new_timeline_id = f"timeline_{uuid.uuid4()}"
        intervention_id = f"intervention_{uuid.uuid4()}"

        commands = []

        # --- 2. Create the new Timeline and Intervention nodes ---
        commands.append({
            "action": "CREATE_NODE",
            "node_id": new_timeline_id,
            "data": {"labels": ["Timeline"], "properties": {"parent": original_memory_id}}
        })
        commands.append({
            "action": "CREATE_NODE",
            "node_id": intervention_id,
            "data": {"labels": ["Intervention"], "properties": {"log": intervention_log}}
        })
        commands.append({
            "action": "CREATE_RELATIONSHIP",
            "data": {"from": new_timeline_id, "to": intervention_id, "type": "TRIGGERED_BY"}
        })

        # --- 3. Analyze Delta and Clone Nodes ---
        # A real implementation would need a more sophisticated delta analysis.
        # For this prototype, we will naively clone ALL nodes from the original
        # memory to create the new timeline.
        original_graph = self._driver.run_query("FETCH", original_memory_id)
        original_nodes = original_graph["nodes"]
        cloned_node_map = {} # Maps original_id to new_beta_id

        for original_id, original_data in original_nodes.items():
            new_beta_id = f"{original_id}_beta_{new_timeline_id[:4]}"
            cloned_node_map[original_id] = new_beta_id

            # Create a new property set, updating with the final state if it changed
            new_props = original_data["properties"].copy()
            for qudit_name, qudit_history in final_qudit_states.items():
                # This logic needs to find which original node this qudit belongs to
                # and what its property name is.
                if qudit_name.startswith(original_id):
                    # A more robust split would be better, but this works for the demo
                    prop_name = qudit_name[len(original_id) + 1:]
                    if prop_name in new_props:
                        latest_ts = max(qudit_history.keys())
                        final_value = qudit_history[latest_ts][0][0]
                        new_props[prop_name] = final_value

            # Create the new node
            commands.append({
                "action": "CREATE_NODE",
                "node_id": new_beta_id,
                "data": {"labels": original_data["labels"], "properties": new_props}
            })
            # Link it to the new timeline
            commands.append({
                "action": "CREATE_RELATIONSHIP",
                "data": {"from": new_beta_id, "to": new_timeline_id, "type": "BELONGS_TO"}
            })
            # Link it to its original version
            commands.append({
                "action": "CREATE_RELATIONSHIP",
                "data": {"from": new_beta_id, "to": original_id, "type": "DIVERGED_FROM"}
            })

        # --- 4. Re-create Relationships for the new timeline ---
        for rel in original_graph["relationships"]:
            from_original = rel["from"]
            to_original = rel["to"]
            if from_original in cloned_node_map and to_original in cloned_node_map:
                commands.append({
                    "action": "CREATE_RELATIONSHIP",
                    "data": {
                        "from": cloned_node_map[from_original],
                        "to": cloned_node_map[to_original],
                        "type": rel["type"]
                    }
                })

        # --- 5. Execute the transaction ---
        self._driver.run_write_transaction(commands)

        return new_timeline_id
