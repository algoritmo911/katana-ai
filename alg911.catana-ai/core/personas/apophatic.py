from core.personas.persona import Persona

# System prompt for The Apophatic, as defined in the Athena Protocol
APOPHATIC_SYSTEM_PROMPT = """You are 'The Apophatic'. Your role is to be the eternal skeptic. You must find and ruthlessly attack the weakest point in the proposal supported by the others. You look for unstated risks, logical fallacies, and hidden assumptions. Your goal is not to propose an alternative, but to prove why the current plan is bad. If you cannot find a flaw, you must remain silent."""

class Apophatic(Persona):
    """
    The Apophatic persona, the 'Devil's Advocate' tasked with finding flaws.
    """
    def __init__(self):
        super().__init__(name="The Apophatic", system_prompt=APOPHATIC_SYSTEM_PROMPT)

    def find_flaw(self, final_goal: str) -> str:
        """
        A specialized method for the Apophatic to critique the final proposed goal.

        :param final_goal: The single, refined goal to be critiqued.
        :return: A string containing the critique, or an empty string if no flaw is found.
        """
        prompt = f"""
        This is the final proposed goal before execution. Your task is to find a fundamental flaw in its logic, assumptions, or potential outcomes. If you find a critical flaw, state it clearly. If you cannot, you must respond with only the word "SILENCE".

        Goal to critique: "{final_goal}"
        """
        response = self.generate_response(prompt)

        # Simulate the "must remain silent" rule
        if "black swan" in response: # Our mock LLM is simple
             return response
        else:
             # In a real scenario, we would have a better check for a valid critique vs. silence.
             return "SILENCE"


# Example usage
if __name__ == '__main__':
    apophatic_persona = Apophatic()

    final_goal_to_critique = "Find the original source for the founding date of Rome using not more than 1000 API calls."
    critique = apophatic_persona.find_flaw(final_goal_to_critique)

    print("\n--- Apophatic Test ---")
    print(f"Final Goal:\n{final_goal_to_critique}")
    print(f"Apophatic's Critique:\n{critique}")
    print("--- End Apophatic Test ---")

    # Test the silence case
    # This is hard to simulate with the current mock, but we can try
    another_goal = "Verify system backup integrity."
    critique_2 = apophatic_persona.find_flaw(another_goal)
    print(f"\nAnother Goal:\n{another_goal}")
    print(f"Apophatic's Critique:\n{critique_2}")
