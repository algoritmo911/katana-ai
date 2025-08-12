import datetime
from typing import Dict

from .contracts import OperatorState, SensorInput

class OperatorModelManager:
    """
    Manages the lifecycle of OperatorState models. It synthesizes raw sensor
    data into a coherent, evolving model of the operator's state.
    """
    def __init__(self):
        # This should be a persistent store like Redis or a database in a real system.
        self.states: Dict[str, OperatorState] = {}

        # These weights should be in a config file for tuning.
        self.weights = {
            'cognitive_load': {'imperative': 0.6, 'complexity': 0.4},
            'emotional_valence': {'sentiment': 1.0}
        }
        # The decay factor determines how much "memory" the state has.
        # A higher value means past states have more influence.
        # The previous value of 0.95 was too high, making the model unresponsive.
        # A value of 0.4 makes the model highly reactive to the last input.
        self.decay_factor = 0.4

    def get_state(self, user_id: str) -> OperatorState:
        """Retrieves or creates a new state for a given user."""
        if user_id not in self.states:
            print(f"ECHO_MANAGER: No state found for user '{user_id}'. Creating a new default state.")
            self.states[user_id] = OperatorState(
                user_id=user_id,
                last_updated_utc=datetime.datetime.now(datetime.timezone.utc)
            )
        return self.states[user_id]

    def update_state(self, sensor_input: SensorInput):
        """
        Updates an operator's state using a new sensor input package.
        This uses an exponential moving average (EMA) to smoothly update values.
        """
        state = self.get_state(sensor_input.user_id)

        # --- Update Cognitive Load ---
        # Final algorithm: Cognitive load is an aggregate of multiple factors,
        # with negative sentiment being a primary driver.

        # 1. Negative sentiment is a powerful indicator of stress/load.
        # We invert the score so that -1.0 sentiment becomes a +1.0 impulse.
        impulse_from_valence = -sensor_input.linguistic.sentiment_score * 0.7

        # 2. Other factors are additive.
        impulse_from_imperative = sensor_input.linguistic.imperative_score * 0.2
        impulse_from_complexity = sensor_input.linguistic.complexity_score * 0.3
        impulse_from_terseness = sensor_input.linguistic.terseness_score * 0.3

        # 3. Combine all factors and clip to a max of 1.0
        new_load_impulse = min(1.0,
            impulse_from_valence +
            impulse_from_imperative +
            impulse_from_complexity +
            impulse_from_terseness
        )

        state.cognitive_load_score = (state.cognitive_load_score * self.decay_factor) + \
                                     (new_load_impulse * (1 - self.decay_factor))

        # --- Update Emotional Valence ---
        new_valence_impulse = sensor_input.linguistic.sentiment_score

        # Make valence change more volatile
        valence_decay = 0.4
        state.emotional_valence = (state.emotional_valence * valence_decay) + \
                                  (new_valence_impulse * (1 - valence_decay))

        # --- TODO: Update Focus Stability ---
        # This would involve comparing the new context_vector to the previous one.
        # A large cosine distance would decrease the stability score.

        # --- Update Context Vector ---
        state.current_context_vector = sensor_input.contextual.context_vector

        state.last_updated_utc = sensor_input.timestamp_utc
        print(f"ECHO_MANAGER: State for user '{state.user_id}' updated. "
              f"Cognitive Load: {state.cognitive_load_score:.2f}, "
              f"Valence: {state.emotional_valence:.2f}")

if __name__ == '__main__':
    # --- Simulation to test the manager ---
    from .sensors.linguistic import LinguisticSensor
    from .sensors.temporal import TemporalSensor
    from .sensors.contextual import ContextualSensor

    # 1. Initialize components
    manager = OperatorModelManager()
    ling_sensor = LinguisticSensor()
    temp_sensor = TemporalSensor()
    cont_sensor = ContextualSensor()
    user_id = "operator_01"

    # 2. Simulate a series of interactions
    print("--- Operator Model Manager Simulation ---")

    # Interaction 1: A neutral question
    text1 = "Could you show me the latest Morpheus report?"
    print(f"\nInput 1: '{text1}'")
    sensor_input1 = SensorInput(
        user_id=user_id,
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc),
        linguistic=ling_sensor.analyze(text1),
        temporal=temp_sensor.analyze(),
        contextual=cont_sensor.analyze(text1)
    )
    manager.update_state(sensor_input1)

    # Interaction 2: An urgent, negative command
    text2 = "This is wrong, get me the logs for the executor immediately. The whole thing is broken."
    print(f"\nInput 2: '{text2}'")
    sensor_input2 = SensorInput(
        user_id=user_id,
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc),
        linguistic=ling_sensor.analyze(text2),
        temporal=temp_sensor.analyze(),
        contextual=cont_sensor.analyze(text2)
    )
    manager.update_state(sensor_input2)

    # Interaction 3: A follow-up, still stressed
    text3 = "Just do it now!"
    print(f"\nInput 3: '{text3}'")
    sensor_input3 = SensorInput(
        user_id=user_id,
        timestamp_utc=datetime.datetime.now(datetime.timezone.utc),
        linguistic=ling_sensor.analyze(text3),
        temporal=temp_sensor.analyze(),
        contextual=cont_sensor.analyze(text3)
    )
    manager.update_state(sensor_input3)

    print("\n--- Final Operator State ---")
    final_state = manager.get_state(user_id)
    print(final_state.model_dump_json(indent=2))

    print("\n--- Simulation Complete ---")
