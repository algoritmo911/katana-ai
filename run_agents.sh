#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

IMAGE_NAME="katana-agent:polis-v1"

# --- Stop and cleanup function ---
stop_and_clean() {
    echo "Stopping and removing existing Katana agent containers..."
    # The '|| true' part ensures that the script doesn't exit if a container doesn't exist
    sudo docker stop katana-agent-1 || true
    sudo docker rm katana-agent-1 || true
    sudo docker stop katana-agent-2 || true
    sudo docker rm katana-agent-2 || true
    echo "Cleanup complete."
}

# --- Main script logic ---
if [ "$1" == "stop" ]; then
    stop_and_clean
    # Optional: also remove volumes if you want a completely fresh start
    # echo "Removing volumes..."
    # sudo docker volume rm katana-data-1 || true
    # sudo docker volume rm katana-data-2 || true
    exit 0
fi

echo "--- Building Katana Agent Docker Image ---"
sudo docker build -t $IMAGE_NAME .
echo "Image '$IMAGE_NAME' built successfully."

# Stop any previous instances before starting new ones
stop_and_clean

echo "\n--- Launching Two Katana Agents ---"

# Launch Agent 1
echo "Launching Agent 1 (ID: katana-1)..."
sudo docker run -d \
    --name katana-agent-1 \
    -e AGENT_ID="katana-1" \
    -v katana-data-1:/app \
    $IMAGE_NAME

# Launch Agent 2
echo "Launching Agent 2 (ID: katana-2)..."
sudo docker run -d \
    --name katana-agent-2 \
    -e AGENT_ID="katana-2" \
    -v katana-data-2:/app \
    $IMAGE_NAME

echo "\n--- Agents Launched Successfully ---"
echo "To see the logs, run: 'sudo docker logs -f [container_name]'"
echo "Example: 'sudo docker logs -f katana-agent-1'"
echo "To stop the agents, run: './run_agents.sh stop'"
echo "\nCurrent running containers:"
sudo docker ps --filter "name=katana-agent"
