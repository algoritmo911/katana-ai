# -*- coding: utf-8 -*-
"""
The Intervention Actuator Daemon.

This component provides a high-level API for external agents (users, other AI)
to intervene in a running simulation. It translates simple commands into
formal Gallifreyan operations and executes them.
"""

from katana.gallifreyan.ast import InterventionGate
from katana.gallifreyan.compiler import Compiler
from katana.gallifreyan.simulator import QuantumStateSimulator


class InterventionActuator:
    """
    Translates high-level commands into quantum interventions and applies them.
    """

    def __init__(self, compiler: Compiler, simulator: QuantumStateSimulator):
        self._compiler = compiler
        self._simulator = simulator

    def intervene(self, intervention_command: dict):
        """
        Applies a single intervention to the current simulation state.

        Args:
            intervention_command: A dictionary with 'target' (qudit name)
                                  and 'state' (the value to force).
        """
        if not all(k in intervention_command for k in ["target", "state"]):
            raise ValueError("Intervention command must include 'target' and 'state' keys.")

        # 1. Create the AST node for the intervention
        intervention_op = InterventionGate(
            target_qudit=intervention_command["target"],
            force_state_to=intervention_command["state"]
        )

        # 2. Compile a "micro-circuit" for just this one operation
        # Note: In a real QVM, this would be an injection into a running
        # event loop, but for this prototype, we compile and run it directly.
        micro_circuit = [("execute_intervention", intervention_op)]

        # 3. Run the micro-circuit on the simulator
        self._compiler.run(micro_circuit, self._simulator)
