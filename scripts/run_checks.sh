#!/bin/bash
set -e

# Always create the stderr log file and directory
mkdir -p scripts/
touch scripts/run_checks_stderr.log

# Test output to log for verification
echo "Run checks started at $(date)" >> scripts/run_checks_stderr.log

# Redirect all subsequent stderr to the log file (append mode)
exec 2>> scripts/run_checks_stderr.log

echo "Running linters..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

echo "Running formatters..."
black .

echo "Running tests with coverage..."
coverage run -m pytest --disable-warnings tests/
echo "Generating coverage report..."
coverage report -m
# Optional: uncomment to generate HTML report
# coverage html

echo "All checks passed!"
