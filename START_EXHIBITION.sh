#!/bin/bash

echo "=============================================================="
echo "                  EXHIBITION SYSTEM"
echo "=============================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    exit 1
fi

# Check if config exists
if [ ! -f "exhibition_config.json" ]; then
    echo "ERROR: exhibition_config.json not found!"
    echo "Please make sure the config file is in the same folder."
    exit 1
fi

echo "Starting exhibition controller..."
echo ""
echo "The system will:"
echo "  - Auto-detect your directories"
echo "  - Generate new objects every 10 minutes"
echo "  - Auto-refresh the 3D viewer"
echo "  - Open browser automatically"
echo ""
echo "=============================================================="
echo "            PRESS CTRL+C TO STOP EVERYTHING"
echo "=============================================================="
echo ""

# Run the controller
python3 exhibition_controller.py

echo ""
echo "Exhibition stopped."
