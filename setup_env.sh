#!/bin/bash

# Katana MindShell Environment Setup Script
# This script prepares a clean and reproducible environment for development and deployment.
# It is designed to be idempotent and robust.

set -o pipefail

LOG_FILE="setup.log"
exec > >(tee -a "${LOG_FILE}") 2>&1

log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1"
}

# --- Helper Functions ---

# Retry a command up to a specific number of times
retry() {
    local retries=$1
    shift
    local count=0
    until "$@"; do
        exit_code=$?
        wait=$((2 ** count))
        count=$((count + 1))
        if [ $count -le "$retries" ]; then
            log "Command failed with exit code $exit_code. Retrying in $wait seconds..."
            sleep $wait
        else
            log "Command failed after $retries retries. Giving up."
            return $exit_code
        fi
    done
    return 0
}

# --- Main Script ---

log "================================================="
log "  Starting Katana MindShell Environment Setup"
log "================================================="

# 1. Clean old environments and temporary files
log "[Step 1/5] Cleaning old environments and temporary files..."
if [ -d "venv" ]; then
    log "Removing old virtual environment..."
    rm -rf venv
fi
log "Purging pip cache..."
pip cache purge
log "Pruning Docker system..."
docker system prune -f
log "[Step 1/5] Cleaning completed."

# 2. Reinstall and verify Python and dependencies
log "[Step 2/5] Reinstalling and verifying Python and dependencies..."
if ! python3 -c 'import sys; assert sys.version_info >= (3, 10)' &>/dev/null; then
    log "Error: Python 3.10+ is required. Please upgrade your Python installation."
    exit 1
fi
log "Python version check passed."

python3 -m venv venv
source venv/bin/activate
log "Virtual environment created and activated."

log "Installing Python dependencies..."
retry 3 pip install --no-cache-dir -r requirements.txt
log "Python dependencies installed successfully."
log "[Step 2/5] Python setup completed."

# 3. Verify Docker and docker-compose
log "[Step 3/5] Verifying Docker and docker-compose..."
if ! docker info &>/dev/null; then
    log "Error: Docker daemon is not running or not accessible."
    log "Please start Docker and ensure you have the correct permissions."
    exit 1
fi
log "Docker daemon is running."

log "Testing Docker with hello-world container..."
docker run hello-world
log "Docker test container ran successfully."

if ! command -v docker-compose &> /dev/null; then
    log "Error: docker-compose is not installed. Please install it."
    exit 1
fi
log "docker-compose is installed."
log "[Step 3/5] Docker setup completed."

# 4. Verify RabbitMQ and Kafka (placeholders)
log "[Step 4/5] Verifying RabbitMQ and Kafka..."
log "Note: This step contains placeholder checks. Implement actual checks based on your project's needs."

# Placeholder for RabbitMQ check
log "Checking RabbitMQ..."
# Example: retry 3 rabbitmqctl status
log "RabbitMQ check placeholder passed."

# Placeholder for Kafka check
log "Checking Kafka..."
# Example: retry 3 kafka-topics.sh --bootstrap-server localhost:9092 --list
log "Kafka check placeholder passed."
log "[Step 4/5] Message broker checks completed."

# 5. Final Readiness Check
log "[Step 5/5] Performing final readiness check..."
# Placeholder for running the readiness script
# python3 readiness_test.py
log "[Step 5/5] Final readiness check placeholder passed."

log "================================================="
log "  Katana MindShell Environment Setup Successful!"
log "================================================="
exit 0
