#!/bin/bash
echo "Starting Visio Bridge MCP Server..."
echo ""
echo "Make sure the local Visio Bridge API is running on port 5100"
echo ""

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Warning: Virtual environment not found. Make sure dependencies are installed."
fi

# Start the server
python visio_bridge_server.py

# If we get here, the server has stopped
echo ""
echo "Server has stopped."
