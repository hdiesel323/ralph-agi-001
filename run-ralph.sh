#!/bin/zsh
#
# RALPH-AGI Runner
# Usage: ./run-ralph.sh [arguments]
#

# Get the directory where this script is located
SCRIPT_DIR="${0:a:h}"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Auto-load .env file
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Run ralph-agi with all arguments passed to this script
ralph-agi "$@"
