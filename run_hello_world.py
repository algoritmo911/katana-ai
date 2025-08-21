# -*- coding: utf-8 -*-
"""
The 'Quantum Hello, World!' for the Gallifreyan Language.

This script demonstrates a full end-to-end execution of a simple
Gallifreyan program, from AST definition to compilation and simulation.
"""

from katana.gallifreyan.ast import (
    SimulationBlueprint,
    TemporalQuditDeclaration,
    Objective,
    GateApplication,
    Measurement,
)
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator


def create_hello_world_blueprint() -> SimulationBlueprint:
    """
    Creates the AST for a simple 'Hello, World!' program.
    """
    # 1. Declare the qudits (temporal registers) we will use.
    hello_qudit = TemporalQuditDeclaration(
        name="HelloWorldQudit",
        initial_states={"t_0": "INITIAL_STATE"}
    )

    # 2. Define the objective of the simulation.
    #    The goal is to apply a gate and then measure the result.
    objective = Objective(
        name="ObserveSuperposition",
        operations=[
            GateApplication(
                gate_name="TARDIS_Gate",
                target_qudit="HelloWorldQudit"
            ),
            Measurement(
                target_qudit="HelloWorldQudit",
                result_name="final_greeting"
            )
        ]
    )

    # 3. Assemble the final blueprint for the simulation.
    blueprint = SimulationBlueprint(
        name="HelloWorldSimulation",
        reality_source="synthetic/test_case",
        qudits=[hello_qudit],
        objective=objective
    )
    return blueprint


def main():
    """
    Main execution function.
    """
    print("--- Gallifreyan v0.1 ---")
    print("--- Quantum Hello, World! ---")

    # 1. Define the program using the AST.
    print("\n[1] Defining SimulationBlueprint AST...")
    blueprint = create_hello_world_blueprint()
    print("... Blueprint created.")
    print(f"    - Objective: {blueprint.objective.name}")
    print(f"    - Qudits: {[q.name for q in blueprint.qudits]}")

    # 2. Instantiate the core components.
    compiler = Compiler()
    simulator = QuantumStateSimulator()

    # 3. Compile the AST into a Quantum Circuit.
    print("\n[2] Compiling blueprint into a quantum circuit...")
    circuit = compiler.compile(blueprint)
    print(f"... Circuit compiled with {len(circuit)} steps.")
    for i, (cmd, op) in enumerate(circuit):
        print(f"    - Step {i}: {cmd} ({op.__class__.__name__})")

    # 4. Execute the circuit on the simulator.
    print("\n[3] Executing circuit on the QuantumStateSimulator...")
    results = compiler.run(circuit, simulator)
    print("... Execution complete.")

    # 5. Print the final, measured result.
    final_result = results.get("final_greeting")
    print("\n[4] Measurement complete. The wave function has collapsed!")
    print(f"    >>> Final measured state: {final_result}")
    print("\n--- Simulation End ---")


if __name__ == "__main__":
    main()
