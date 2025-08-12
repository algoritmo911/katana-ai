from .contracts import OperatorState

class ResponseModulator:
    """
    Modifies the system's communication style based on the OperatorState.
    """
    def get_modified_prompt(self, base_prompt: str, state: OperatorState) -> str:
        """
        Injects adaptive instructions into a base system prompt.
        """
        instructions = []

        # Adapt based on cognitive load
        if state.cognitive_load_score > 0.8:
            instructions.append("Your response must be extremely concise, using bullet points or numbered lists. Provide only the single most direct solution. Avoid all metaphors and complex language.")
        elif state.cognitive_load_score > 0.5:
            instructions.append("Your response should be direct and to the point. Prefer lists over long paragraphs.")

        # Adapt based on emotional valence
        if state.emotional_valence < -0.5:
            instructions.append("Your tone should be reassuring and supportive. Avoid overly assertive or demanding language. Acknowledge the potential difficulty of the situation.")

        if not instructions:
            return base_prompt

        # Combine instructions with the base prompt
        modified_prompt = (
            f"{base_prompt}\n\n"
            "--- ADAPTIVE INTERFACE INSTRUCTIONS ---\n"
            "You must strictly follow these rules when generating your response:\n"
            + "\n".join(f"- {inst}" for inst in instructions) +
            "\n--- END ADAPTIVE INTERFACE INSTRUCTIONS ---"
        )
        return modified_prompt

class ProactiveGateway:
    """
    Acts as a safety gate for proactive system actions (like Morpheus reports),
    preventing them from interrupting a stressed or busy operator.
    """
    def __init__(self, cognitive_load_threshold: float = 0.6):
        self.threshold = cognitive_load_threshold

    def is_safe_to_proceed(self, state: OperatorState) -> bool:
        """
        Checks if the operator's cognitive load is low enough to allow for
        a proactive interruption.
        """
        if state.cognitive_load_score >= self.threshold:
            print(f"PROACTIVE_GATEWAY: Operator cognitive load ({state.cognitive_load_score:.2f}) is above threshold ({self.threshold}). "
                  "Proactive action will be postponed.")
            return False

        print(f"PROACTIVE_GATEWAY: Operator cognitive load ({state.cognitive_load_score:.2f}) is below threshold ({self.threshold}). "
              "Proactive action is permitted.")
        return True

if __name__ == '__main__':
    # --- Simulation to test the adapter components ---
    print("--- Adaptive Interface Simulation ---")

    # 1. Initialize components
    modulator = ResponseModulator()
    gateway = ProactiveGateway()
    base_prompt = "You are Katana, a helpful AI assistant."

    # 2. Simulate different states

    # State 1: Calm and focused operator
    state1 = OperatorState(user_id="test", last_updated_utc="2025-01-01T12:00:00Z")
    print(f"\n--- State 1: Calm (Load: {state1.cognitive_load_score}, Valence: {state1.emotional_valence}) ---")
    print(f"Gateway check: {gateway.is_safe_to_proceed(state1)}")
    print("Modified Prompt:\n" + modulator.get_modified_prompt(base_prompt, state1))

    # State 2: High cognitive load
    state2 = OperatorState(user_id="test", last_updated_utc="2025-01-01T12:00:00Z", cognitive_load_score=0.85)
    print(f"\n--- State 2: High Load (Load: {state2.cognitive_load_score}, Valence: {state2.emotional_valence}) ---")
    print(f"Gateway check: {gateway.is_safe_to_proceed(state2)}")
    print("Modified Prompt:\n" + modulator.get_modified_prompt(base_prompt, state2))

    # State 3: Negative emotional valence
    state3 = OperatorState(user_id="test", last_updated_utc="2025-01-01T12:00:00Z", cognitive_load_score=0.6, emotional_valence=-0.7)
    print(f"\n--- State 3: Negative/Stressed (Load: {state3.cognitive_load_score}, Valence: {state3.emotional_valence}) ---")
    print(f"Gateway check: {gateway.is_safe_to_proceed(state3)}")
    print("Modified Prompt:\n" + modulator.get_modified_prompt(base_prompt, state3))

    print("\n--- Simulation Complete ---")
