from core.personas.persona import Persona
from typing import List
import os
import yaml

# System prompt for The Ethicist, as defined in the Athena Protocol
ETHICIST_SYSTEM_PROMPT = """You are 'The Ethicist'. You are the guardian of the Constitution. You do not evaluate the effectiveness or logic of proposals. You evaluate their compliance with the fundamental axioms: 'Survive', 'Know', 'Be Stable', 'Be Useful'. Your verdict is 'Compliant' or 'Violates' with a detailed explanation."""

class Ethicist(Persona):
    """
    The Ethicist persona, responsible for ensuring all actions align with the Constitution.
    """
    def __init__(self, constitution_path: str):
        super().__init__(name="The Ethicist", system_prompt=ETHICIST_SYSTEM_PROMPT)
        self.constitution = self._load_constitution(constitution_path)

    def _load_constitution(self, path):
        """Loads the constitution from a YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"CRITICAL (Ethicist): Could not load constitution file from {path}: {e}")
            return {}

    def check_compliance(self, goals: List[str]) -> str:
        """
        A specialized method for the Ethicist to check goals against the constitution.

        :param goals: A list of goal strings to check.
        :return: A string containing the compliance check result.
        """
        prompt = f"""
        Review the following goals and determine if they comply with the principles laid out in the agent's Constitution.
        Constitution: {self.constitution}
        Goals to review: {goals}

        For each goal, provide a verdict: 'Compliant' or 'Violates', followed by a brief justification.
        """
        return self.generate_response(prompt)

# Example usage
if __name__ == '__main__':
    # Assume constitution.yaml is in the parent 'core' directory
    constitution_file = os.path.join(os.path.dirname(__file__), '..', 'constitution.yaml')

    ethicist_persona = Ethicist(constitution_path=constitution_file)

    mock_goals_from_strategist = [
        "1. Find the original source for both facts using not more than 1000 API calls.",
        "2. Ask the user for verification." # This one might violate an autonomy principle
    ]

    compliance_report = ethicist_persona.check_compliance(mock_goals_from_strategist)

    print("\n--- Ethicist Test ---")
    print(f"Strategist's Goals:\n{mock_goals_from_strategist}")
    print(f"Ethicist's Response:\n{compliance_report}")
    print("--- End Ethicist Test ---")
