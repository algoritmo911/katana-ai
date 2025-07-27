#!/bin/bash
set -e

# Activate the virtual environment
source venv/bin/activate

# Add the bin directory to the PATH to find the doppler executable
export PATH=$PATH:$(pwd)/bin

# Check for required environment variables
while read -r line; do
  if [[ -n "$line" && "$line" != *"#"* ]]; then
    varname=$(echo "$line" | cut -d '=' -f 1)
    if [ -z "${!varname}" ]; then
      echo "WARNING: Environment variable $varname is not set."
    fi
  fi
done < .env.example

# Run the main application with Doppler
doppler run -- python3 main.py
