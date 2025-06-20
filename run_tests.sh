#!/bin/bash

# Script to discover and run all unit tests in the Katana project

# Set the project root directory (assuming this script is in the root)
PROJECT_ROOT=$(dirname "$0")

# Ensure the script is run from the project root for consistent path discovery
cd "$PROJECT_ROOT"

# Set PYTHONPATH to include the project root if it's not already discoverable
# This helps Python find the 'katana' package and its modules.
export PYTHONPATH=".:$PYTHONPATH"

# Set a default log level for tests if not already set
# This ensures consistent behavior for logger initialization during tests.
export KATANA_LOG_LEVEL=${KATANA_LOG_LEVEL:-"WARNING"}

echo "Running Katana Project Unit Tests..."
echo "PYTHONPATH: $PYTHONPATH"
echo "KATANA_LOG_LEVEL: $KATANA_LOG_LEVEL"

# Discover and run tests within the 'katana' directory
# -v for verbose output
python3 -m unittest discover -s ./katana -p 'test_*.py' -v

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed successfully!"
else
    echo "Some tests failed. Exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
