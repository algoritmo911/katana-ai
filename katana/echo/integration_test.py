import asyncio
import datetime

from .sensors.linguistic import LinguisticSensor
from .sensors.temporal import TemporalSensor
from .sensors.contextual import ContextualSensor
from .manager import OperatorModelManager
from .adapter import ResponseModulator, ProactiveGateway
from .contracts import SensorInput

class EchoSystem:
    """A simple facade to represent the integrated Echo system."""
    def __init__(self):
        self.ling_sensor = LinguisticSensor()
        self.temp_sensor = TemporalSensor()
        self.cont_sensor = ContextualSensor()
        self.manager = OperatorModelManager()
        self.modulator = ResponseModulator()
        self.gateway = ProactiveGateway()
        self.base_prompt = "You are Katana, a helpful AI assistant."

    def process_input(self, user_id: str, text: str):
        """Simulates receiving and processing one user input."""
        print(f"\n>>> INPUT from [{user_id}]: '{text}'")

        # 1. Log temporal event
        self.temp_sensor.log_request()

        # 2. Gather sensor data
        sensor_input = SensorInput(
            user_id=user_id,
            timestamp_utc=datetime.datetime.now(datetime.timezone.utc),
            linguistic=self.ling_sensor.analyze(text),
            temporal=self.temp_sensor.analyze(),
            contextual=self.cont_sensor.analyze(text)
        )

        # 3. Update the operator model
        self.manager.update_state(sensor_input)

        # 4. Get the current state and adapt behavior
        state = self.manager.get_state(user_id)

        # 5. Modulate the response prompt
        modified_prompt = self.modulator.get_modified_prompt(self.base_prompt, state)
        print(f"\n--- MODULATED PROMPT ---\n{modified_prompt}\n------------------------")

        # 6. Check the proactive gateway
        print(f"--- GATEWAY CHECK ---")
        self.gateway.is_safe_to_proceed(state)
        print(f"---------------------")


async def run_echo_integration_test():
    """
    This test simulates a conversation with a user who is becoming
    progressively more stressed and frustrated.
    """
    print("\n" + "#"*60)
    print("# ECHO PROTOCOL: FULL INTEGRATION TEST")
    print("#"*60)

    system = EchoSystem()
    user_id = "operator_alpha"

    # --- SCENARIO ---

    # 1. A calm, simple start
    system.process_input(user_id, "Can you show me the Morpheus Protocol TDD?")
    await asyncio.sleep(1)

    # 2. A more complex, slightly more demanding request
    system.process_input(user_id, "Okay, now I need you to cross-reference that with the REMExecutor implementation and find any discrepancies.")
    await asyncio.sleep(1)

    # 3. A frustrated, urgent, and negative command
    system.process_input(user_id, "This is taking too long. The executor's rollback mechanism is flawed. Forget the TDD, just show me the code for the git client now!")
    await asyncio.sleep(1)

    # 4. A very short, clipped command, indicating high stress
    system.process_input(user_id, "Just the code. No explanations.")

    print("\n" + "#"*60)
    print("# INTEGRATION TEST COMPLETE")
    print("#"*60)


if __name__ == "__main__":
    # This test needs the spaCy models. The other files handle this,
    # but we can add a check here too.
    try:
        import spacy
        spacy.load("en_core_web_md")
    except OSError:
        print("Integration test requires 'en_core_web_md'. Please run 'katana/echo/sensors/contextual.py' first to download it.")
    else:
        asyncio.run(run_echo_integration_test())
