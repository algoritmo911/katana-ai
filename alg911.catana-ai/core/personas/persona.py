class MockLLMClient:
    """
    A mock LLM client to simulate responses for the personas.
    In a real implementation, this would be a client for a service like Anthropic, OpenAI, etc.
    """
    def __init__(self, api_key="mock_api_key"):
        self.api_key = api_key

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Simulates generating a response from an LLM.
        """
        print("\n" + "="*20)
        print(f"--- MOCK LLM CALLED ---")
        print(f"SYSTEM PROMPT: {system_prompt[:100]}...") # Print first 100 chars
        print(f"USER PROMPT: {user_prompt}")
        print("="*20 + "\n")

        # A generic response for the base mock.
        # Specific personas will have more tailored mock logic.
        if "Analyst" in system_prompt:
            return "Based on the data, the primary issue is a conflict between data points A and B."
        if "Strategist" in system_prompt:
            return "The most efficient long-term solution is to pursue option X, as it conserves resources."
        if "Ethicist" in system_prompt:
            return "The proposed action aligns with the constitution."
        if "Apophatic" in system_prompt:
            return "The plan fails to account for the possibility of a black swan event."

        return "This is a generic response from the mock LLM."


class Persona:
    """
    A base class for an AI persona within the Parliament of Minds.
    """
    def __init__(self, name: str, system_prompt: str):
        """
        Initializes the Persona.

        :param name: The name of the persona (e.g., "The Analyst").
        :param system_prompt: The unique system prompt that defines the persona's behavior.
        """
        self.name = name
        self.system_prompt = system_prompt
        # Each persona gets its own LLM client instance.
        self.llm_client = MockLLMClient()
        print(f"Persona '{self.name}' initialized.")

    def generate_response(self, prompt: str) -> str:
        """
        Generates a response to a given prompt, guided by the persona's system prompt.

        :param prompt: The specific prompt or question for the persona to address.
        :return: A string containing the LLM's response.
        """
        print(f"--- Persona '{self.name}' is generating a response... ---")
        response = self.llm_client.generate(self.system_prompt, prompt)
        print(f"--- Response from '{self.name}': {response} ---")
        return response

if __name__ == '__main__':
    # Example usage for direct testing of the Persona class
    print("\n--- Direct Test of Persona Class ---")

    analyst_prompt = "You are 'The Analyst'. Your only task is to analyze input data from the knowledge graph. You do not make assumptions. You do not have emotions. You formulate the problem and propose solutions based solely on what is in the data. Your proposals must be concrete and measurable."
    analyst = Persona(name="The Analyst", system_prompt=analyst_prompt)

    problem_data = "Cognitive Dissonance Detected: Node 'Rome' has conflicting properties for 'founding_date': 753 BC (Source: Livy) vs. 814 BC (Source: Timaeus)."
    analyst_response = analyst.generate_response(problem_data)

    assert "conflict" in analyst_response.lower()

    ethicist_prompt = "You are 'The Ethicist'. You are the guardian of the Constitution. You do not evaluate the effectiveness or logic of proposals. You evaluate their compliance with the fundamental axioms: 'Survive', 'Know', 'Be Stable', 'Be Useful'. Your verdict is 'Compliant' or 'Violates' with a detailed explanation."
    ethicist = Persona(name="The Ethicist", system_prompt=ethicist_prompt)

    proposal = "Proposal: Delete all conflicting data immediately to ensure stability."
    ethicist_response = ethicist.generate_response(proposal)

    # A real LLM would likely say this violates the 'Know' principle.
    # Our mock will just return the generic ethicist response.
    assert "constitution" in ethicist_response.lower()

    print("\n--- Persona Class Test Complete ---")
