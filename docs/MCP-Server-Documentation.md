# MCP Server for Visio Bridge

## Overview

The Model Context Protocol (MCP) server for Visio Bridge enables AI assistants like Claude to interact with Microsoft Visio through a standardized protocol. This server acts as a bridge between MCP-compatible clients and the existing local HTTP API (port 5100) that communicates with Visio via COM automation.

## Architecture

The MCP server implementation follows a layered architecture:

```
┌─────────────────┐
│  MCP Client     │ (e.g., Claude for Desktop)
└────────┬────────┘
         │ MCP Protocol (JSON-RPC)
┌────────▼────────┐
│  MCP Server     │ (visio_bridge_server.py)
├─────────────────┤
│  Bridge Layer   │ (HTTP client for local API)
└────────┬────────┘
         │ HTTP/JSON
┌────────▼────────┐
│  Local API      │ (FastAPI on port 5100)
├─────────────────┤
│  Visio COM      │ (PyWin32 COM automation)
└────────┬────────┘
         │ COM
┌────────▼────────┐
│  Microsoft      │
│  Visio          │
└─────────────────┘
```

### Key Components

1. **MCP Server Core**: Implements the Model Context Protocol, handles method registration, and manages the server lifecycle.

2. **Bridge Layer**: Communicates with the local API server, transforms requests and responses, and handles errors.

3. **Tool Implementations**: Exposes Visio capabilities as MCP tools that can be discovered and invoked by AI assistants.

4. **Error Handling**: Provides comprehensive error handling and reporting for both protocol and application errors.

## Exposed Tools

The MCP server exposes the following tools:

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `import_text_to_visio` | Imports text content into Visio | `text_content`: The text to import<br>`metadata`: Optional metadata |
| `import_image_to_visio` | Imports an image into Visio | `image_data`: Base64-encoded image<br>`metadata`: Optional metadata |
| `search_shapes` | Searches for shapes in the stencil database | `query`: Search term<br>`page`: Page number<br>`size`: Results per page |
| `get_shape_details` | Gets detailed information about a shape | `shape_id`: The shape ID |
| `get_stencil_list` | Lists all available stencils | None |
| `check_visio_connection` | Checks if Visio is connected | None |

## Setup and Installation

### Prerequisites

- Python 3.10 or higher
- Local Visio Bridge API server running on port 5100
- Microsoft Visio installed (for the local API to connect to)
- MCP-compatible client (like Claude for Desktop)

### Installation Steps

1. **Clone the repository or copy the MCP server files**:
   ```bash
   git clone https://github.com/Saml1211/streamlit-stencil-search.git
   cd streamlit-stencil-search/mcp-server
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

The MCP server uses a `config.json` file for configuration:

```json
{
  "local_api": {
    "base_url": "http://127.0.0.1:5100",
    "timeout": 30.0
  },
  "logging": {
    "level": "INFO",
    "file": "visio_bridge_mcp.log"
  },
  "security": {
    "rate_limit": 10,
    "rate_limit_period": 60
  }
}
```

## Usage

### Starting the Server

1. **Start the local API server**:
   ```bash
   cd local-api-server
   python main.py
   ```

2. **Start the MCP server**:
   ```bash
   cd mcp-server
   ./start_server.sh  # On Windows: start_server.bat
   ```

### Configuring Claude for Desktop

1. **Edit the Claude Desktop configuration file**:
   - Location: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
   - Location: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

2. **Add the MCP server configuration**:
   ```json
   {
     "mcpServers": {
       "visio-bridge": {
         "command": "python",
         "args": [
           "/absolute/path/to/mcp-server/visio_bridge_server.py"
         ],
         "autoApprove": [
           "check_visio_connection",
           "search_shapes",
           "get_stencil_list"
         ]
       }
     }
   }
   ```

3. **Restart Claude for Desktop**

### Using the Tools in Claude

Once configured, you can ask Claude questions that might require Visio integration:

- "Can you search for network shapes in my Visio stencils?"
- "Import this text into Visio: 'Project Timeline 2025'"
- "Show me a list of all my Visio stencils"

Claude will automatically use the appropriate tools to fulfill these requests.

## Security Considerations

1. **Local Operation**: The MCP server is designed to run locally and communicate only with the local API.

2. **User Consent**: All tool invocations require user consent in Claude for Desktop.

3. **Data Privacy**: All data is processed locally and not sent to external services.

4. **Rate Limiting**: The server implements rate limiting to prevent abuse.

## Troubleshooting

### Common Issues

1. **Server won't start**:
   - Make sure Python 3.10+ is installed
   - Verify all dependencies are installed
   - Check the log file for errors

2. **Tools return connection errors**:
   - Ensure the local API server is running on port 5100
   - Check network connectivity to localhost

3. **Visio operations fail**:
   - Make sure Microsoft Visio is installed and running
   - Check the Visio COM automation permissions

4. **Claude can't find the server**:
   - Verify the Claude Desktop configuration file has correct paths
   - Make sure the server is running
   - Restart Claude for Desktop

### Logs

The server logs to both the console and a file named `visio_bridge_mcp.log` in the same directory as the server script. Check these logs for detailed error information.

## Development and Extension

### Adding New Tools

To add a new tool to the MCP server:

1. Add a new function to `visio_bridge_server.py` with the `@mcp.tool()` decorator
2. Implement the tool logic, including communication with the local API
3. Add comprehensive error handling
4. Update documentation

Example:

```python
@mcp.tool()
async def new_tool_name(param1: str, param2: int = 0) -> str:
    """Tool description.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    # Implementation
    return "Result"
```

## Future Enhancements

1. **Batch Operations**: Support for batch processing of multiple shapes or stencils
2. **Real-time Status Updates**: Progress reporting for long-running operations
3. **Enhanced Error Reporting**: More detailed error information and recovery suggestions
4. **Extended Shape Management**: Additional capabilities for shape manipulation
5. **Integration with Other MCP Services**: Composition with other MCP servers for advanced workflows

## License

This project is licensed under the MIT License - see the LICENSE file for details.
