# -*- coding: utf-8 -*-
"""
Tests for the QuantumCanvas Simulator.

This test suite verifies the basic functionality of the QuantumCanvas class,
ensuring that the API methods work as expected and the class state is consistent.
"""

import unittest
import sys
import os

# Add the parent directory to the Python path to allow module import
# This is a common pattern for simple project structures.
# We add the path to the 'quantum_canvas' directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulator import QuantumCanvas

class TestQuantumCanvas(unittest.TestCase):
    """Test cases for the QuantumCanvas simulator scaffold."""

    def setUp(self):
        """Set up a new QuantumCanvas instance for each test."""
        self.canvas = QuantumCanvas(max_atoms=10)

    def test_initialization(self):
        """Test that the canvas is initialized correctly."""
        self.assertIsInstance(self.canvas, QuantumCanvas)
        self.assertEqual(len(self.canvas.atoms), 0)
        self.assertEqual(self.canvas.max_atoms, 10)

    def test_add_atom(self):
        """Test adding a single atom."""
        atom_id = self.canvas.add_atom('C', (0.0, 0.0, 0.0))
        self.assertEqual(atom_id, 0)
        self.assertEqual(len(self.canvas.atoms), 1)
        self.assertIn(0, self.canvas.atoms)
        self.assertEqual(self.canvas.atoms[0]['element'], 'C')

    def test_add_multiple_atoms(self):
        """Test adding multiple atoms."""
        id1 = self.canvas.add_atom('H', (1.0, 0.0, 0.0))
        id2 = self.canvas.add_atom('O', (0.0, 0.0, 0.0))
        id3 = self.canvas.add_atom('H', (-1.0, 0.0, 0.0))
        self.assertEqual(len(self.canvas.atoms), 3)
        self.assertEqual(id1, 0)
        self.assertEqual(id2, 1)
        self.assertEqual(id3, 2)

    def test_atom_limit(self):
        """Test that adding atoms beyond the max limit raises an error."""
        canvas = QuantumCanvas(max_atoms=2)
        canvas.add_atom('A', (0,0,0))
        canvas.add_atom('B', (1,1,1))
        with self.assertRaises(ValueError):
            canvas.add_atom('C', (2,2,2))

    def test_simulation_run(self):
        """Test that the simulation step runs without errors."""
        self.canvas.add_atom('Fe', (0,0,0))
        self.canvas.run_simulation_step()
        # Check that simulation time has advanced
        self.assertGreater(self.canvas.simulation_time, 0)

    def test_get_system_state(self):
        """Test retrieving the system state."""
        self.canvas.add_atom('C', (0,0,0))
        self.canvas.add_atom('O', (1.2,0,0))
        state = self.canvas.get_system_state()
        self.assertEqual(len(state), 2)
        self.assertEqual(state[0]['element'], 'C')
        self.assertEqual(state[1]['id'], 1)

    def test_get_material_properties(self):
        """Test retrieving material properties."""
        self.canvas.add_atom('Si', (0,0,0))
        props = self.canvas.get_material_properties()
        self.assertIsInstance(props, dict)
        self.assertEqual(props['status'], 'ok')
        self.assertEqual(props['num_atoms'], 1)

if __name__ == '__main__':
    # This allows running the tests directly from the command line
    unittest.main()
