#!/bin/sh

# Function to display help
show_help() {
  echo "Usage: $0 [options]"
  echo
  echo "Options:"
  echo "  --dev       Run in development mode."
  echo "  --prod      Run in production mode."
  echo "  --test      Run tests."
  echo "  --help      Show this help message."
}

# Default mode
MODE="dev"

# Parse arguments
if [ "$1" = "--help" ]; then
  show_help
  exit 0
elif [ "$1" = "--dev" ]; then
  MODE="dev"
elif [ "$1" = "--prod" ]; then
  MODE="prod"
elif [ "$1" = "--test" ]; then
  MODE="test"
fi

# Activate virtual environment
if [ -f "bot/venv/bin/activate" ]; then
  . bot/venv/bin/activate
else
  echo "Virtual environment not found. Please run 'python3 -m venv bot/venv' first."
  exit 1
fi

# Run based on mode
case "$MODE" in
  "dev")
    echo "Running in development mode..."
    python bot/katana_bot.py
    ;;
  "prod")
    echo "Running in production mode..."
    # Add production-specific commands here
    python bot/katana_bot.py
    ;;
  "test")
    echo "Running tests..."
    pytest -v
    ;;
esac
