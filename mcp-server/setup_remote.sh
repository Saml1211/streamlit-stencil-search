#!/bin/bash

# Configuration script for remote Visio Bridge setup

# Default values
DEFAULT_WINDOWS_IP="192.168.1.100"  # Replace with your Windows machine's IP
DEFAULT_API_KEY="YOUR_API_KEY_HERE"  # Replace with the API key from Windows

# Get values from command line or use defaults
WINDOWS_IP=${1:-$DEFAULT_WINDOWS_IP}
API_KEY=${2:-$DEFAULT_API_KEY}

# Export environment variables
export VISIO_BRIDGE_API_URL="http://${WINDOWS_IP}:5100"
export VISIO_BRIDGE_API_KEY="${API_KEY}"

echo "Remote Visio Bridge configuration:"
echo "Windows IP: ${WINDOWS_IP}"
echo "API URL: ${VISIO_BRIDGE_API_URL}"
echo "API Key: ${API_KEY}"
echo ""
echo "Environment variables set. Now run the MCP server with:"
echo "./start_server.sh"
echo ""
echo "Or to start the server directly:"
echo "python visio_bridge_server.py"
echo ""
echo "To make these settings permanent, add the following to your ~/.bashrc or ~/.zshrc:"
echo "export VISIO_BRIDGE_API_URL=\"http://${WINDOWS_IP}:5100\""
echo "export VISIO_BRIDGE_API_KEY=\"${API_KEY}\""

# Start a new shell with the environment variables set
exec $SHELL
