# -*- coding: utf-8 -*-
"""
The Gallifreyan "Compiler"

This module translates a Gallifreyan AST (a SimulationBlueprint object)
into a "Quantum Circuit", which is a linear sequence of commands that
the QuantumStateSimulator can execute.
"""
from typing import List, Tuple, Any, Dict

from .ast import GateApplication, Measurement, SimulationBlueprint, InterventionGate
from .simulator import QuantumStateSimulator

# A circuit is a list of (command_name, command_object) tuples
QuantumCircuit = List[Tuple[str, Any]]


class Compiler:
    """
    Translates a Gallifreyan program AST into an executable circuit.
    """

    def __init__(self):
        pass

    def compile(self, blueprint: SimulationBlueprint) -> QuantumCircuit:
        """
        Processes a SimulationBlueprint and returns a list of simulator commands.
        """
        circuit: QuantumCircuit = []

        # Step 1: Load the initial state of the universe (the blueprint)
        circuit.append(("load_blueprint", blueprint))

        # Step 2: Translate the objective's operations into a sequence
        if blueprint.objective and blueprint.objective.operations:
            for op in blueprint.objective.operations:
                if isinstance(op, GateApplication):
                    circuit.append(("execute_gate", op))
                elif isinstance(op, Measurement):
                    circuit.append(("execute_measurement", op))
                elif isinstance(op, InterventionGate):
                    circuit.append(("execute_intervention", op))
                else:
                    raise TypeError(f"Unknown operation type in objective: {type(op)}")

        return circuit

    def run(self, circuit: QuantumCircuit, simulator: QuantumStateSimulator) -> Dict[str, Any]:
        """
        Executes a compiled circuit on a given simulator.
        Returns a dictionary of results from measurement operations.
        """
        results = {}
        for command, obj in circuit:
            if command == "load_blueprint":
                simulator.load_blueprint(obj)
            elif command == "execute_gate":
                simulator.execute_gate(obj)
            elif command == "execute_intervention":
                simulator.execute_intervention(obj)
            elif command == "execute_measurement":
                result = simulator.execute_measurement(obj)
                results[obj.result_name] = result
            else:
                raise ValueError(f"Unknown command in circuit: {command}")

        return results
