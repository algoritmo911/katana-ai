import sys
import os
import datetime

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from neurovault.state import get_current_katana_state
from neurovault.memory_policy import MemoryPolicyManager

# Define the path to the "remote" repository for logging and state.
# We use a relative path to navigate from neurovault/ to sapiens_notes_private/
SAPIENS_NOTES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../sapiens_notes_private/checkpoints')
)


def main():
    """
    Simulates the process of creating and storing a state checkpoint.
    This script mimics the `feature/katana-dynamic-monitoring` behavior.
    """
    print("--- Starting Katana State Checkpoint Process ---")

    # 1. Initialize the Memory Policy Manager
    manager = MemoryPolicyManager()

    # 2. Get the current state of the Katana system
    print("Aggregating current system state...")
    current_state = get_current_katana_state()

    # 3. Create the serialized checkpoint from the state
    print("Serializing state to create checkpoint...")
    checkpoint_data = manager.create_checkpoint(current_state)

    # 4. Define the checkpoint filename with a timestamp
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    filename = f"state_{timestamp}.json"
    filepath = os.path.join(SAPIENS_NOTES_PATH, filename)

    # 5. Write the checkpoint to the sapiens_notes_private "repository"
    print(f"Writing checkpoint to: {filepath}")
    try:
        os.makedirs(SAPIENS_NOTES_PATH, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(checkpoint_data)
        print("Checkpoint successfully written.")
    except IOError as e:
        print(f"Error: Failed to write checkpoint file. {e}")
        return

    # 6. Simulate the Git process
    print("\n--- Simulating Git Operations ---")
    print(f"git -C ../sapiens_notes_private add checkpoints/{filename}")
    print(f"git -C ../sapiens_notes_private commit -m \"feat(state): Add checkpoint {timestamp}\"")
    print("git -C ../sapiens_notes_private push origin feature/katana-dynamic-monitoring")
    print("--- Checkpoint Process Complete ---")


if __name__ == "__main__":
    main()
