import sys
import os

# Add the project root to the path so we can import katana_cli
sys.path.insert(0, os.path.abspath('.'))

from katana_cli.core import kubernetes

if __name__ == "__main__":
    print("--- Running Stage 2 Test: Creating Cluster ---")
    success = kubernetes.create_cluster()
    if success:
        print("--- Cluster creation successful ---")
    else:
        print("--- Cluster creation failed ---")
        sys.exit(1)
