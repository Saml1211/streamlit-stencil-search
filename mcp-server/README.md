# Visio Bridge MCP Server

This server exposes Visio integration capabilities through the Model Context Protocol (MCP), allowing other MCP-compatible tools to interact with the local Visio bridge.

## Overview

The Visio Bridge MCP Server acts as a bridge between MCP clients (like Claude for Desktop) and the local Visio Bridge API running on port 5100. It enables AI assistants to:

- Import text content into Visio
- Import images into Visio
- Search for shapes in the stencil database
- Get detailed information about shapes and stencils
- Check the connection status of Visio

## Prerequisites

- Python 3.10 or higher
- Local Visio Bridge API server running on port 5100
- Microsoft Visio installed (for the local API to connect to)
- MCP-compatible client (like Claude for Desktop)

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Make sure the local Visio Bridge API is running on port 5100
2. Start the MCP server:
   ```bash
   python visio_bridge_server.py
   ```

3. Configure your MCP client to use this server

### Claude for Desktop Configuration

To use this server with Claude for Desktop, add the following to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "visio-bridge": {
      "command": "python",
      "args": [
        "/path/to/visio_bridge_server.py"
      ]
    }
  }
}
```

Replace `/path/to/visio_bridge_server.py` with the absolute path to the server script.

## Available Tools

The server exposes the following tools:

- `import_text_to_visio`: Import text content into Visio
- `import_image_to_visio`: Import a base64-encoded image into Visio
- `search_shapes`: Search for shapes in the stencil database
- `get_shape_details`: Get detailed information about a specific shape
- `get_stencil_list`: Get a list of all available stencils
- `check_visio_connection`: Check if the local Visio instance is connected

## Troubleshooting

- **Server won't start**: Make sure Python 3.10+ is installed and all dependencies are installed
- **Tools return connection errors**: Ensure the local Visio Bridge API is running on port 5100
- **Visio operations fail**: Make sure Microsoft Visio is installed and running
- **Claude can't find the server**: Check your Claude Desktop configuration file for correct paths

## Logs

The server logs to both the console and a file named `visio_bridge_mcp.log` in the same directory as the server script.

## Security Considerations

- This server is designed to run locally and communicate only with the local Visio Bridge API
- It does not expose any network services beyond what's required for MCP communication
- All user data is processed locally and not sent to external services

## License

This project is licensed under the MIT License - see the LICENSE file for details.
