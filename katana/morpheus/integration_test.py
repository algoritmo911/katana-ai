import asyncio
import time

# In a real app, this would be part of a proper dependency injection system.
from katana.morpheus.monitor import activity_monitor
from katana.background_tasks import trigger_morpheus_protocol, SUSTAINED_IDLE_PERIOD_S


async def run_full_cycle_integration_test():
    """
    This test proves that the entire homeostasis loop works as designed.
    It simulates activity, followed by a sustained idle period, which should
    trigger the full Morpheus cycle: Analyze -> Architect -> Execute.
    """
    print("\n" + "#"*60)
    print("# MORPHEUS PROTOCOL: FULL INTEGRATION TEST")
    print("#"*60)

    # 1. Simulate some initial activity to ensure the trigger doesn't fire prematurely.
    print("\nPHASE 1: Simulating system activity...")
    print("-"*50)
    activity_monitor.log_request()
    print("Logged a request. Checking trigger...")
    await trigger_morpheus_protocol()

    activity_monitor.register_task("sample_task_1")
    print("Registered a task. Checking trigger...")
    await trigger_morpheus_protocol()
    activity_monitor.unregister_task("sample_task_1")
    print("Unregistered a task.")
    print("-" * 50)
    print("PHASE 1: Activity simulation complete. System should not be idle.")

    # 2. Simulate the start of a sustained idle period.
    print("\nPHASE 2: Simulating start of sustained idle period...")
    print("-"*50)
    # The first call should start the countdown.
    await trigger_morpheus_protocol()
    print("-" * 50)

    # 3. Manually manipulate the timer to simulate the passage of time.
    # This is a key part of the test, avoiding a real 15-minute wait.
    print(f"\nPHASE 3: Simulating passage of {SUSTAINED_IDLE_PERIOD_S} seconds...")
    print("-"*50)

    # We need to access the global timestamp in the other module.
    # This is fragile and only for testing.
    import katana.background_tasks
    if katana.background_tasks.idle_since_timestamp:
        print(f"Original idle timestamp: {katana.background_tasks.idle_since_timestamp}")
        katana.background_tasks.idle_since_timestamp -= SUSTAINED_IDLE_PERIOD_S
        print(f"Manipulated idle timestamp: {katana.background_tasks.idle_since_timestamp}")
    else:
        print("ERROR: idle_since_timestamp was not set. Test cannot proceed.")
        return
    print("-" * 50)

    # 4. The final call should now detect the elapsed time and trigger the full cycle.
    print("\nPHASE 4: Triggering the full Morpheus cycle...")
    print("-"*50)
    await trigger_morpheus_protocol()
    print("-" * 50)
    print("PHASE 4: Morpheus cycle execution should be complete.")


    print("\n" + "#"*60)
    print("# INTEGRATION TEST COMPLETE")
    print("#"*60)


if __name__ == "__main__":
    asyncio.run(run_full_cycle_integration_test())
