# MCP Server for Visio Bridge - Quick Start Guide

This guide will help you quickly set up and start using the MCP server for Visio Bridge integration.

## Prerequisites

- Python 3.10 or higher
- Microsoft Visio installed
- Claude for Desktop (or another MCP-compatible client)

## Setup in 5 Minutes

### 1. Install the MCP Server

```bash
# Clone or download the repository
git clone https://github.com/Saml1211/streamlit-stencil-search.git
cd streamlit-stencil-search

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd mcp-server
pip install -r requirements.txt
```

### 2. Start the Local API Server

```bash
# In a new terminal window
cd streamlit-stencil-search/local-api-server
python main.py
```

You should see a message indicating the server is running on port 5100.

### 3. Start the MCP Server

```bash
# In your original terminal window
cd streamlit-stencil-search/mcp-server
python visio_bridge_server.py
```

### 4. Configure Claude for Desktop

1. Open your Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the following configuration (create the file if it doesn't exist):

```json
{
  "mcpServers": {
    "visio-bridge": {
      "command": "python",
      "args": [
        "/absolute/path/to/streamlit-stencil-search/mcp-server/visio_bridge_server.py"
      ]
    }
  }
}
```

Replace `/absolute/path/to/` with the actual path to your repository.

3. Restart Claude for Desktop

### 5. Test the Integration

1. Open Claude for Desktop
2. Ask Claude: "Can you check if my Visio connection is working?"
3. Claude should use the `check_visio_connection` tool and report the status

## Available Tools

- **Import text to Visio**: "Import this text into Visio: 'Hello World'"
- **Search shapes**: "Find network shapes in my Visio stencils"
- **List stencils**: "Show me a list of all my Visio stencils"
- **Get shape details**: "Tell me about shape ID 123"
- **Check connection**: "Is Visio connected and ready?"

## Troubleshooting

- **Claude can't find the server**: Make sure the path in the configuration is correct and the server is running
- **Connection errors**: Ensure both the local API server and Visio are running
- **Tool execution errors**: Check the logs in `mcp-server/visio_bridge_mcp.log`

## Next Steps

For more detailed information, see the full [MCP Server Documentation](MCP-Server-Documentation.md).
