# -*- coding: utf-8 -*-
"""
The Incarnator Daemon.

This daemon reads a memory from the Neurovault (a graph database) and
transforms it into an initial quantum state (a SimulationBlueprint AST)
for the Quantum Simulator.
"""
from katana.gallifreyan.ast import (
    SimulationBlueprint,
    TemporalQuditDeclaration,
    HandshakeDeclaration,
    Objective,
)
from katana.neurovault.mock_db import MockNeurovaultDriver

# Defines how to handle uncertainty for missing properties.
# If a 'Person' node is missing a 'mood', it will be put into a
# superposition of these states.
UNCERTAINTY_MAP = {
    "Person": {
        "mood": ["happy", "sad", "neutral", "curious"],
    }
}

class Incarnator:
    """
    Transforms classical memory graphs into quantum simulation blueprints.
    """

    def __init__(self, driver: MockNeurovaultDriver):
        self._driver = driver

    def incarnate_memory(self, memory_id: str) -> SimulationBlueprint:
        """
        Fetches a memory graph and generates a SimulationBlueprint AST.
        """
        graph_data = self._driver.run_query("FETCH MEMORY", memory_id=memory_id)

        qudits = []
        handshakes = []

        # --- Probabilistic State Initializer Logic ---
        for node_id, node_data in graph_data["nodes"].items():
            initial_states = {}
            # Convert known properties to collapsed states
            for prop_name, prop_value in node_data["properties"].items():
                initial_states[prop_name] = prop_value

            # Handle uncertainty for missing properties
            node_labels = node_data.get("labels", [])
            for label in node_labels:
                if label in UNCERTAINTY_MAP:
                    for prop_name, possible_states in UNCERTAINTY_MAP[label].items():
                        if prop_name not in initial_states:
                            # This property is missing, create a superposition
                            initial_states[prop_name] = possible_states

            # Create a separate qudit for each property
            for prop_name, prop_value in initial_states.items():
                qudit_name = f"{node_id}_{prop_name}"
                qudit = TemporalQuditDeclaration(
                    name=qudit_name,
                    initial_states={"t_0": prop_value}
                )
                qudits.append(qudit)

        # --- Entanglement Weaver Logic ---
        for rel in graph_data["relationships"]:
            # Entangle every property of the source node with every property of the target node.
            # This is a simplification; a real system would have more specific rules.
            from_node_props = graph_data["nodes"][rel["from"]]["properties"].keys()
            to_node_props = graph_data["nodes"][rel["to"]]["properties"].keys()
            for from_prop in from_node_props:
                for to_prop in to_node_props:
                    handshake = HandshakeDeclaration(
                        qudit1=f"{rel['from']}_{from_prop}",
                        qudit2=f"{rel['to']}_{to_prop}"
                    )
                    handshakes.append(handshake)

        # Create a default objective for the simulation
        objective = Objective(
            name=f"ExploreMemory_{memory_id}",
            operations=[] # No operations by default, just setup
        )

        blueprint = SimulationBlueprint(
            name=f"Incarnation_{memory_id}",
            reality_source=f"neurovault.memory_id('{memory_id}')",
            objective=objective,
            qudits=qudits,
            handshakes=handshakes
        )

        return blueprint
