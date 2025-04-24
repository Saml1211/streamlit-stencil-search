# Visio Bridge MCP Server

This directory contains the implementation of the Visio Bridge MCP (Model Context Protocol) server.

## Overview

The MCP server acts as a bridge between an AI assistant (like Cursor) and the Local API server (`local_api_server.py`). It exposes tools that the AI can call to interact with Microsoft Visio via the local API.

## Components

- `mcp_server.py`: The main script for the MCP server.
- `mcp_tools.py`: Defines the tools exposed by the MCP server.
- `config.py`: Handles configuration loading.

## Running the Server

Ensure the Local API server is running first. Then, run the MCP server from the project root directory:

```bash
venv\Scripts\python.exe visio_bridge/mcp_server.py --api-url <local_api_server_url>
```

Replace `<local_api_server_url>` with the actual URL of the running local API server (e.g., `http://127.0.0.1:8001`).

## Testing

For testing and debugging the MCP server, the `MCP Inspector` tool is recommended.

See the **MCP Inspector** section in `memory-bank/techContext.md` for setup and usage instructions. 