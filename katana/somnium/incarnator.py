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
        # A map to define the 'main' property for a given node type for entanglement
        PRIMARY_PROPERTY_MAP = {
            "Person": "mood",
            "Key": "type",
            "Door": "state",
        }

        for rel in graph_data["relationships"]:
            from_node_id = rel["from"]
            to_node_id = rel["to"]
            from_node_data = graph_data["nodes"][from_node_id]
            to_node_data = graph_data["nodes"][to_node_id]

            # Find the primary property for each node in the relationship
            from_prop = next((p for t, p in PRIMARY_PROPERTY_MAP.items() if t in from_node_data["labels"]), None)
            to_prop = next((p for t, p in PRIMARY_PROPERTY_MAP.items() if t in to_node_data["labels"]), None)

            if from_prop and to_prop:
                # Check if the properties actually exist for these nodes before creating a handshake
                if from_prop in from_node_data["properties"] and to_prop in to_node_data["properties"]:
                    handshake = HandshakeDeclaration(
                        qudit1=f"{from_node_id}_{from_prop}",
                        qudit2=f"{to_node_id}_{to_prop}"
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
