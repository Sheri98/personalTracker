#!/bin/bash
# Run Personal Task Tracker

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "Error: Python is not installed"
    exit 1
fi

# Run the tracker
cd "$SCRIPT_DIR"
$PYTHON personal_tracker.py
