import os
import subprocess
from typing import List

class SyncAgent:
    def __init__(self, remote_path: str):
        self.remote_path = remote_path

    def sync_memories(self, memory_dir: str):
        """Synchronizes the memories to the remote path using rclone."""
        # This is a placeholder for the actual rclone command.
        # The user will need to have rclone configured for this to work.
        # The command will be something like:
        # rclone sync memory_dir remote_path
        print(f"Syncing memories from {memory_dir} to {self.remote_path}")
        try:
            subprocess.run(["rclone", "sync", memory_dir, self.remote_path], check=True)
            print("Sync complete.")
        except FileNotFoundError:
            print("rclone not found. Please install and configure rclone.")
        except subprocess.CalledProcessError as e:
            print(f"Error during sync: {e}")
