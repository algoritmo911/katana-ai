# =======================================================================================================================
# ID ПРОТОКОЛА: Telos-v1.0-TheSeagullNebula
# КОМПОНЕНТ: The World Modeler (Моделировщик Мира)
# ОПИСАНИЕ: Создает и поддерживает целостную, вероятностную модель реальности.
# =======================================================================================================================

import datetime
import json
import os
from typing import List, Dict, Any

# Adjust path to import from the parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import WorldStateSnapshot, NeurovaultSummary, DiagnostReport, CassandraPrediction
from core.neurovault import Neurovault
from core.diagnost import Diagnost
from core.cassandra import Cassandra

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(AGENT_DIR, "katana.history.json")

class WorldModeler:
    """
    The World Modeler daemon. Its purpose is to create a coherent snapshot
    of the agent's internal and external reality, which can be used for simulations.
    """
    def __init__(self, neurovault: Neurovault, diagnost: Diagnost, cassandra: Cassandra):
        self.neurovault = neurovault
        self.diagnost = diagnost
        self.cassandra = cassandra

    def _load_action_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Loads the most recent entries from the agent's action history.
        """
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
                # Return the last `limit` items
                return history[-limit:]
        except (json.JSONDecodeError, IndexError):
            return []

    def create_world_state_snapshot(self) -> WorldStateSnapshot:
        """
        Aggregates data from all input sources into a single, coherent
        WorldStateSnapshot object.
        """
        # 1. Get data from all sources
        knowledge_summary_data = self.neurovault.get_knowledge_summary()
        system_health_data = self.diagnost.get_system_health_report()
        predictions_data = self.cassandra.get_predictions()
        action_history = self._load_action_history()

        # 2. Create Pydantic models from the raw data
        knowledge_summary = NeurovaultSummary(**knowledge_summary_data)

        # The predictions data is nested, so we need to flatten it for the model
        flat_predictions_data = predictions_data['next_hour_predictions']
        flat_predictions_data['predictability_score'] = predictions_data['predictability_score']

        system_health = DiagnostReport(**system_health_data)
        predictions = CassandraPrediction(**flat_predictions_data)

        # 3. Assemble the final snapshot
        snapshot = WorldStateSnapshot(
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            knowledge=knowledge_summary,
            system_health=system_health,
            predictions=predictions,
            action_history=action_history
        )

        return snapshot

if __name__ == '__main__':
    # --- Test ---
    # Initialize the placeholder components
    mock_neurovault = Neurovault()
    mock_diagnost = Diagnost()
    mock_cassandra = Cassandra()

    # Initialize the WorldModeler with the mock components
    world_modeler = WorldModeler(
        neurovault=mock_neurovault,
        diagnost=mock_diagnost,
        cassandra=mock_cassandra
    )

    # Create a snapshot
    world_state = world_modeler.create_world_state_snapshot()

    print("--- WorldModeler Placeholder ---")
    print("Generated WorldStateSnapshot:")
    print(world_state.model_dump_json(indent=2))

    assert world_state.knowledge.total_concepts > 0
    assert world_state.system_health.cpu_load_percent > 0
    assert world_state.predictions.predictability_score > 0
    print("\n--- WorldModeler Verified ---")
