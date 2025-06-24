import sys
import os

# Add the parent directory of 'katana' to sys.path
# This assumes 'katana' is a top-level directory in the project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from katana.self_evolve import SelfEvolver
    print("Successfully imported SelfEvolver from katana.self_evolve")
    evolver = SelfEvolver()
    evolver.evolve()
except ImportError as e:
    print(f"Error importing SelfEvolver: {e}")
    print("Please ensure 'katana/self_evolve.py' exists and SelfEvolver class is defined.")
    print("Current sys.path:", sys.path)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
