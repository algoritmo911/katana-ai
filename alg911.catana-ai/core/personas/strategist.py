from core.personas.persona import Persona
from typing import List

# System prompt for The Strategist, as defined in the Athena Protocol
STRATEGIST_SYSTEM_PROMPT = """You are 'The Strategist'. Your task is to think about consequences. You evaluate proposals from 'The Analyst' in terms of their impact on the long-term survival and development of the system. You manage resources. You look not for the most obvious, but for the most effective solution. You always ask the question: 'How will this help us in a year?'"""

class Strategist(Persona):
    """
    The Strategist persona, focused on long-term planning and resource efficiency.
    """
    def __init__(self):
        super().__init__(name="The Strategist", system_prompt=STRATEGIST_SYSTEM_PROMPT)

    def evaluate_goals(self, goals: List[str]) -> str:
        """
        A specialized method for the Strategist to evaluate proposed goals.

        :param goals: A list of goal strings proposed by the Analyst.
        :return: A string containing the evaluation and a recommendation.
        """
        # In a real implementation, this would access system resource monitors and plan history.
        prompt = f"""
        Evaluate the following goals proposed by the Analyst. Consider long-term impact and resource cost. Reject goals that are inefficient or propose a more effective alternative.
        Goals: {goals}
        """
        return self.generate_response(prompt)

# Example usage
if __name__ == '__main__':
    strategist_persona = Strategist()
    mock_goals = [
        "1. Find the original source for both facts.",
        "2. Cross-analyze all related entities.",
        "3. Ask the user for verification."
    ]
    strategic_evaluation = strategist_persona.evaluate_goals(mock_goals)

    print("\n--- Strategist Test ---")
    print(f"Analyst's Goals:\n{mock_goals}")
    print(f"Strategist's Response:\n{strategic_evaluation}")
    print("--- End Strategist Test ---")
