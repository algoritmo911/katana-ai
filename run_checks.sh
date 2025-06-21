#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Running Katana Bot Checks..."
echo "============================"

# 1. Run tests with coverage (using pytest)
echo ""
echo "Step 1: Running tests with coverage..."
echo "------------------------------------"
# Ensure pytest and pytest-cov are installed
if ! python -m pytest --version &> /dev/null; then
    echo "Error: pytest is not installed. Please install it using: pip install pytest pytest-cov"
    exit 1
fi
if ! python -c "import pytest_cov" &> /dev/null; then
    echo "Error: pytest-cov is not installed. Please install it using: pip install pytest-cov (it should be a dependency of pytest-cov, but check explicitly)"
    exit 1
fi
python -m pytest --cov=. --cov-report=term-missing --cov-fail-under=80 test_bot.py

echo ""
echo "Tests and coverage check completed."
echo "------------------------------------"

# 2. Run isort to check import sorting
echo ""
echo "Step 2: Checking import sorting with isort..."
echo "-------------------------------------------"
# Ensure isort is installed
if ! python -m isort --version &> /dev/null; then
    echo "Error: isort is not installed. Please install it using: pip install isort"
    exit 1
fi
python -m isort --check-only --diff .

echo ""
echo "isort check completed."
echo "-------------------------------------------"

# 3. Run flake8 for linting
echo ""
echo "Step 3: Running flake8 for linting..."
echo "-----------------------------------"
# Ensure flake8 is installed
if ! python -m flake8 --version &> /dev/null; then
    echo "Error: flake8 is not installed. Please install it using: pip install flake8"
    exit 1
fi
python -m flake8 .

echo ""
echo "flake8 linting completed."
echo "-----------------------------------"

# 4. Run black to check formatting
echo ""
echo "Step 4: Checking code formatting with black..."
echo "--------------------------------------------"
# Ensure black is installed
if ! python -m black --version &> /dev/null; then
    echo "Error: black is not installed. Please install it using: pip install black"
    exit 1
fi
python -m black --check --diff .

echo ""
echo "black formatting check completed."
echo "--------------------------------------------"

echo ""
echo "============================"
echo "All checks passed successfully!"
