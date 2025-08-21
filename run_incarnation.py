# -*- coding: utf-8 -*-
"""
The Incarnation Demonstrator for the Somnium Protocol.

This script demonstrates the full pipeline of:
1. Reading a memory from the (mock) Neurovault.
2. Using the Incarnator to transform it into a SimulationBlueprint AST.
3. Compiling the AST into a Quantum Circuit.
4. Executing the circuit to see the initial state and the effect of a measurement.
"""
import json
from katana.neurovault.mock_db import get_driver
from katana.somnium.incarnator import Incarnator
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator
from katana.gallifreyan.ast import Measurement

def pretty_print_blueprint(bp):
    """Helper to print a summary of the blueprint."""
    print(f"  - Blueprint Name: {bp.name}")
    print(f"  - Reality Source: {bp.reality_source}")
    print(f"  - Qudits Created ({len(bp.qudits)}):")
    for q in bp.qudits:
        state_t0 = q.initial_states.get('t_0')
        state_str = f"{state_t0[:2]}..." if isinstance(state_t0, list) and len(state_t0) > 2 else state_t0
        print(f"    - {q.name}: {state_str}")
    print(f"  - Entanglements Created ({len(bp.handshakes)}):")
    # Just print the first few for brevity
    for h in bp.handshakes[:3]:
        print(f"    - {h.qudit1} <--> {h.qudit2}")
    if len(bp.handshakes) > 3:
        print(f"    - ... and {len(bp.handshakes) - 3} more.")

def pretty_print_final_state(sim):
    """Helper to print the final state of all qudits."""
    print("\n[4] Final State of All Qudits after Measurement:")
    for name, history in sim.qudits.items():
        latest_ts = max(history.keys())
        state = history[latest_ts]
        print(f"  - {name}: {state}")


def main():
    """Main execution function."""
    print("--- Somnium Protocol - Phase 1: The Incarnation ---")

    # 1. Instantiate the driver and Incarnator
    driver = get_driver()
    incarnator = Incarnator(driver)

    # 2. Generate a blueprint from a memory in the mock Neurovault
    print("\n[1] Incarnating memory 'mem-123' from Neurovault...")
    blueprint = incarnator.incarnate_memory("mem-123")
    print("... Incarnation complete. Blueprint generated:")
    pretty_print_blueprint(blueprint)

    # 3. Add a measurement to the objective to see what happens
    # We will measure the mood of person_b, which was uncertain.
    blueprint.objective.operations.append(
        Measurement(target_qudit="person_b_mood", result_name="measured_mood")
    )
    print("\n[2] Added a measurement operation to the objective: Measure 'person_b_mood'.")

    # 4. Compile and execute the full circuit
    compiler = Compiler()
    simulator = QuantumStateSimulator()

    print("\n[3] Compiling and executing the full circuit...")
    circuit = compiler.compile(blueprint)
    results = compiler.run(circuit, simulator)
    print("... Execution complete.")

    measured_mood = results.get("measured_mood")
    print(f"    >>> Measured mood of person_b: {measured_mood}")

    # 5. Print the final state of the whole system
    pretty_print_final_state(simulator)

    driver.close()
    print("\n--- Simulation End ---")


if __name__ == "__main__":
    main()
