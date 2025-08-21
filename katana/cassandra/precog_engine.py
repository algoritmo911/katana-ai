# -*- coding: utf-8 -*-
"""
The Precog Engine (Движок Предсказания)

Analyzes the present state of the system (the Digital Twin) to generate
a probabilistic tree of possible future states.
"""
import copy
import uuid
from datetime import datetime, timedelta

from katana.diagnostics.service_map import ServiceMap

# --- Prediction Constants ---
HIGH_LATENCY_THRESHOLD_MS = 200.0
HIGH_ERROR_RATE_THRESHOLD = 0.05
PREDICTION_TIMESTEP_MINUTES = 5
CASCADE_FAILURE_PROBABILITY = 0.8


class PrecogEngine:
    """
    Generates Probabilistic Future Trees (PFTs) from the system's Digital Twin.
    """

    def __init__(self, digital_twin: ServiceMap):
        self.digital_twin = digital_twin
        # In the future, this will hold an ensemble of predictive models (LSTM, GNN, etc.)
        self.models = []

    def _create_pft_node(self, state_change, source, probability, parent_state):
        """Helper to create a new PFT node."""
        future_time = datetime.utcnow() + timedelta(minutes=PREDICTION_TIMESTEP_MINUTES)
        node = {
            "id": f"pft_node_{uuid.uuid4()}",
            "timestamp": future_time.isoformat(),
            "state_change": state_change,
            "prediction_source": source,
            "probability": probability,
            "children": [],
        }
        # Apply the state change to a copy of the parent state for the next level
        node["full_state_after_change"] = self._apply_state_change(parent_state, state_change)
        return node

    def _apply_state_change(self, original_state, state_change):
        """Applies a state change to a copy of the state."""
        new_state = copy.deepcopy(original_state)
        for service, changes in state_change.items():
            if service in new_state:
                new_state[service].update(changes)
        return new_state


    def generate_pft(self):
        """
        Generates a Probabilistic Future Tree using simple rule-based logic.
        """
        now = datetime.utcnow()
        current_state = {name: data for name, data in self.digital_twin.graph.nodes(data=True)}

        pft = {
            "pft_version": "1.0",
            "generated_at": now.isoformat(),
            "root_node": {
                "id": "root",
                "timestamp": now.isoformat(),
                "state": current_state,
                "probability": 1.0,
                "children": [],
            },
        }

        # Rule-based prediction logic
        for service_name, data in current_state.items():
            metrics = data.get("metrics", {})

            # Rule 1: High Latency Prediction
            if metrics.get("latency", 0) > HIGH_LATENCY_THRESHOLD_MS:
                state_change = {service_name: {"status": "PREDICTED_FAILURE_LATENCY"}}
                node = self._create_pft_node(
                    state_change, "RuleBased_HighLatency", 0.75, current_state
                )
                pft["root_node"]["children"].append(node)

            # Rule 2: High Error Rate Prediction
            if metrics.get("error_rate", 0) > HIGH_ERROR_RATE_THRESHOLD:
                state_change = {service_name: {"status": "PREDICTED_FAILURE_ERRORS"}}
                node = self._create_pft_node(
                    state_change, "RuleBased_HighErrorRate", 0.85, current_state
                )
                pft["root_node"]["children"].append(node)

        # Rule 3: Cascading Failure Prediction
        # We do this in a second pass to react to the predictions we just made.
        # This is a simplified, one-level cascade prediction.
        new_predictions = []
        for prediction_node in pft["root_node"]["children"]:
            for service_name, change in prediction_node["state_change"].items():
                if "PREDICTED_FAILURE" in change.get("status", ""):
                    # This service is predicted to fail, check its dependencies
                    downstream_services = self.digital_twin.get_blast_radius(service_name)
                    for downstream_service in downstream_services:
                        # Avoid predicting failure for a service that's already failing
                        if "PREDICTED_FAILURE" in prediction_node["full_state_after_change"][downstream_service].get("status", ""):
                            continue

                        state_change = {downstream_service: {"status": "PREDICTED_CASCADE_FAILURE"}}
                        # Create a child node for the *original* prediction node
                        cascade_node = self._create_pft_node(
                            state_change,
                            f"RuleBased_Cascade_from_{service_name}",
                            prediction_node["probability"] * CASCADE_FAILURE_PROBABILITY,
                            prediction_node["full_state_after_change"]
                        )
                        prediction_node["children"].append(cascade_node)

        return pft
