import time
import yaml
import asyncio

# In a real app, this would be part of a proper dependency injection system.
from katana.morpheus.monitor import activity_monitor
from katana.morpheus.main import run_morpheus_cycle

# Load config
with open("katana/morpheus/morpheus_config.yml", "r") as f:
    config = yaml.safe_load(f)

SUSTAINED_IDLE_PERIOD_S = config['circadian_rhythm']['sleep_conditions']['sustained_idle_period_seconds']

# This state should be in a shared store like Redis in a multi-process environment.
# For this implementation, a global variable suffices.
idle_since_timestamp = None

# This function would be decorated with a scheduler decorator in a real application,
# e.g., @chronos.schedule(every="1 minute")
async def trigger_morpheus_protocol():
    """
    This background task acts as the "hypothalamus" of the system, checking
    regularly if the conditions for "sleep" (the Morpheus Protocol) are met.
    """
    global idle_since_timestamp

    if activity_monitor.is_idle():
        if idle_since_timestamp is None:
            # This is the first moment of idleness. Record the time.
            idle_since_timestamp = time.time()
            print(f"MORPHEUS_TRIGGER: System is now idle. Starting countdown of {SUSTAINED_IDLE_PERIOD_S}s.")

        idle_duration = time.time() - idle_since_timestamp
        print(f"DEBUG: System has been idle for {idle_duration:.2f} seconds.")

        if idle_duration >= SUSTAINED_IDLE_PERIOD_S:
            print(f"MORPHEUS_TRIGGER: Sustained idle period of {SUSTAINED_IDLE_PERIOD_S}s reached. Starting Morpheus Protocol.")
            try:
                await run_morpheus_cycle()
            except Exception as e:
                print(f"ERROR: Morpheus cycle failed: {e}")
            finally:
                # Reset the timer after the cycle runs, whether it succeeds or fails.
                idle_since_timestamp = None
    else:
        if idle_since_timestamp is not None:
            # The system was idle, but activity has resumed. Reset the countdown.
            print("MORPHEUS_TRIGGER: Activity resumed. Sleep cycle interrupted.")
        idle_since_timestamp = None

if __name__ == "__main__":
    # This file is not meant to be run directly in production.
    # The `trigger_morpheus_protocol` function would be scheduled by Chronos.
    # To test the full loop, run `katana/morpheus/integration_test.py`.
    print("This module defines background tasks and is not meant to be executed directly.")
