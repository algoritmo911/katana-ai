# -*- coding: utf-8 -*-
"""
The Intervention Demonstrator for the Somnium Protocol.

This script demonstrates the "Will" phase of the protocol:
1. A memory is incarnated from the Neurovault into a quantum state.
2. An external agent (the script) decides to intervene.
3. The InterventionActuator forces a change in the simulation.
4. The consequences of this change (the 'shockwave') are observed in the final state.
"""

from katana.neurovault.mock_db import get_driver
from katana.somnium.incarnator import Incarnator
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator
from katana.somnium.intervention_actuator import InterventionActuator

def print_state_summary(sim, step_name):
    """Helper to print the state of key qudits."""
    print(f"\n--- {step_name} ---")
    door_state = sim.qudits.get("object_2_state", {}).get("t_0")
    key_state = sim.qudits.get("object_1_type", {}).get("t_0")
    print(f"  - Door state (object_2_state): {door_state}")
    print(f"  - Key state (object_1_type): {key_state}")


def main():
    """Main execution function."""
    print("--- Somnium Protocol - Phase 2: The Will ---")

    # 1. Setup: Incarnate a memory to get an initial simulation state.
    driver = get_driver()
    incarnator = Incarnator(driver)
    blueprint = incarnator.incarnate_memory("mem-123")

    compiler = Compiler()
    simulator = QuantumStateSimulator()

    # Load the initial state into the simulator
    initial_circuit = compiler.compile(blueprint)
    compiler.run(initial_circuit, simulator)

    print_state_summary(simulator, "Initial State")

    # 2. The Intervention
    print("\n>>> An intervention occurs! Forcing the door (object_2) open.")
    actuator = InterventionActuator(compiler, simulator)

    intervention_command = {
        "target": "object_2_state",
        "state": "open"
    }
    actuator.intervene(intervention_command)

    # 3. Observe the final state
    print_state_summary(simulator, "Final State after Intervention")

    print("\nNote how 'object_1_type' (the key) also changed state because")
    print("it was entangled with the door in the mock memory graph.")

    driver.close()
    print("\n--- Simulation End ---")


if __name__ == "__main__":
    main()
