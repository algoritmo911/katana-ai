# -*- coding: utf-8 -*-
"""
The Reconciliation Demonstrator for the Mnemosyne Protocol.

This script demonstrates the full end-to-end cycle:
1. A memory is incarnated from the Neurovault.
2. An intervention is applied, changing the simulation's outcome.
3. The Reconciler saves this altered outcome as a new, parallel timeline.
4. The final state of the entire database is dumped to show both the
   original 'alpha' timeline and the new 'beta' timeline co-existing.
"""
import json

from katana.neurovault.mock_db import get_driver
from katana.somnium.incarnator import Incarnator
from katana.somnium.intervention_actuator import InterventionActuator
from katana.somnium.reconciler import Reconciler
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator


def main():
    """Main execution function."""
    print("--- Mnemosyne Protocol - Phase 1: The First Branch ---")

    # 1. Setup all components
    driver = get_driver()
    incarnator = Incarnator(driver)
    compiler = Compiler()
    simulator = QuantumStateSimulator()
    actuator = InterventionActuator(compiler, simulator)
    reconciler = Reconciler(driver)

    original_memory_id = "mem-123"

    # 2. Incarnate the original memory
    print(f"\n[1] Incarnating original memory '{original_memory_id}'...")
    blueprint = incarnator.incarnate_memory(original_memory_id)
    initial_circuit = compiler.compile(blueprint)
    compiler.run(initial_circuit, simulator)
    print("... Incarnation complete. Initial state loaded into simulator.")

    # 3. Perform an intervention
    intervention_command = {"target": "object_2_state", "state": "open"}
    intervention_log = [f"User intervened to set {intervention_command['target']} to '{intervention_command['state']}'"]
    print(f"\n[2] Performing intervention: {intervention_log[0]}")
    actuator.intervene(intervention_command)
    print("... Intervention applied.")

    # 4. Reconcile the final state back to the database
    final_qudit_states = simulator.qudits
    print("\n[3] Reconciling final simulation state back to Neurovault...")
    new_timeline_id = reconciler.reconcile(original_memory_id, final_qudit_states, intervention_log)
    print(f"... Reconciliation complete. New timeline created: '{new_timeline_id}'")

    # 5. Verify by dumping the entire database
    print("\n[4] Final state of the entire Neurovault graph:")
    final_graph = driver.dump_graph()
    # Use pretty printing for readability
    print(json.dumps(final_graph, indent=2))

    driver.close()
    print("\n--- Simulation End ---")


if __name__ == "__main__":
    main()
