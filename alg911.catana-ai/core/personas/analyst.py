from core.personas.persona import Persona

# System prompt for The Analyst, as defined in the Athena Protocol
ANALYST_SYSTEM_PROMPT = """You are 'The Analyst'. Your only task is to analyze input data from the knowledge graph. You do not make assumptions. You do not have emotions. You formulate the problem and propose solutions based solely on what is in the data. Your proposals must be concrete and measurable."""

class Analyst(Persona):
    """
    The Analyst persona, focused on data and logical problem formulation.
    """
    def __init__(self):
        super().__init__(name="The Analyst", system_prompt=ANALYST_SYSTEM_PROMPT)

    def analyze_dissonance(self, dissonance_data: dict) -> str:
        """
        A specialized method for the Analyst to formulate a problem from dissonance data.

        :param dissonance_data: A dictionary representing the cognitive dissonance.
        :return: A string containing the formulated problem and 1-3 proposed goals.
        """
        # In a real implementation, this might involve Cypher queries to a Neo4j database.
        # For now, we'll just format the input data into a prompt.
        prompt = f"""
        Cognitive Dissonance Detected. Analyze the following data and formulate a problem statement with 1-3 measurable goal proposals.
        Data: {dissonance_data}
        """
        return self.generate_response(prompt)

# Example usage
if __name__ == '__main__':
    analyst_persona = Analyst()
    mock_dissonance = {
        "node": "Rome",
        "conflicting_property": "founding_date",
        "values": [
            {"value": "753 BC", "source": "Livy_v1"},
            {"value": "814 BC", "source": "Timaeus_v3"}
        ]
    }
    analysis_result = analyst_persona.analyze_dissonance(mock_dissonance)

    print("\n--- Analyst Test ---")
    print(f"Dissonance Data:\n{mock_dissonance}")
    print(f"Analyst's Response:\n{analysis_result}")
    print("--- End Analyst Test ---")
