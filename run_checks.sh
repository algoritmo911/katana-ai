#!/bin/bash

echo "Running linters..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

echo "Running formatters..."
black .

echo "Running tests..."
pytest --disable-warnings tests/

echo "All checks passed!"
