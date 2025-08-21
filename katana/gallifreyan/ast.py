# -*- coding: utf-8 -*-
"""
Gallifreyan Abstract Syntax Tree (AST)

This module defines the data structures that represent a Gallifreyan program.
Instead of a text-based parser, the "compiler" will operate on these
validated Python objects.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

# --- Core Data Types ---
# A state can be a single value or a superposition of values
State = Union[Any, List[Any]]

# A map of timestamps (e.g., 't_0', 't_plus_1') to their state
StateMap = Dict[str, State]


# --- AST Node Definitions ---

@dataclass
class TemporalQuditDeclaration:
    """Declares a temporal register and its initial states."""
    name: str
    initial_states: StateMap = field(default_factory=dict)


@dataclass
class HandshakeDeclaration:
    """Declares an entanglement between two qudits."""
    qudit1: str
    qudit2: str


@dataclass
class GateApplication:
    """Represents applying a gate to a qudit."""
    gate_name: str  # e.g., "TARDIS_Gate"
    target_qudit: str


@dataclass
class Measurement:
    """Represents a measurement operation to collapse a state."""
    target_qudit: str
    perspective: str = "neutral"  # e.g., "optimistic", "pessimistic"
    result_name: str = "final_state"


@dataclass
class InterventionGate:
    """Represents an external intervention to force a qudit into a state."""
    target_qudit: str
    force_state_to: Any


@dataclass
class Objective:
    """Defines the goal of the simulation."""
    name: str
    operations: List[Union[GateApplication, Measurement, InterventionGate]] = field(default_factory=list)


@dataclass
class SimulationBlueprint:
    """The root of the AST, representing a complete Gallifreyan program."""
    name: str
    reality_source: str  # e.g., "neurovault.memory_id('uuid-1234')"
    objective: Objective
    qudits: List[TemporalQuditDeclaration] = field(default_factory=list)
    handshakes: List[HandshakeDeclaration] = field(default_factory=list)
