# Remote Visio Bridge Setup

This guide explains how to set up the MCP server on a Mac to control a remote version of Visio running on a Windows machine.

## Overview

The Visio Bridge consists of three main components:

1. **MCP Server**: Runs on your Mac, communicates with Claude for Desktop
2. **Local API Server**: Runs on the Windows machine, communicates with Visio
3. **Visio**: Runs on the Windows machine

In this remote setup, the MCP server on your Mac will communicate with the Local API server on the Windows machine over your network.

## Prerequisites

- A Mac computer with Python 3.10+ installed
- A Windows machine with:
  - Microsoft Visio installed
  - Python 3.10+ installed
  - Network connectivity to your Mac
- Both machines on the same network (or connected via VPN)

## Setup Instructions

### 1. Windows Machine Setup

1. **Clone the repository on Windows**:
   ```bash
   git clone https://github.com/Saml1211/streamlit-stencil-search.git
   cd streamlit-stencil-search
   ```

2. **Install dependencies**:
   ```bash
   cd local-api-server
   pip install -r requirements.txt
   ```

3. **Start the Local API Server**:
   ```bash
   python main.py
   ```

4. **Note the API Key**:
   When the server starts, it will display an API key. Save this key as you'll need it for your Mac setup.
   ```
   ===== API KEY =====
   your_api_key_here
   ===================
   ```

5. **Note the Windows IP Address**:
   Open a command prompt and run:
   ```
   ipconfig
   ```
   Look for the IPv4 address (usually starts with 192.168.x.x or 10.x.x.x).

### 2. Mac Setup

1. **Clone the repository on Mac**:
   ```bash
   git clone https://github.com/Saml1211/streamlit-stencil-search.git
   cd streamlit-stencil-search
   ```

2. **Install dependencies**:
   ```bash
   cd mcp-server
   pip install -r requirements.txt
   ```

3. **Configure the remote connection**:
   Use the provided setup script with your Windows IP and API key:
   ```bash
   ./setup_remote.sh windows_ip_address your_api_key
   ```
   
   Alternatively, you can manually edit `visio_bridge_server.py` and update:
   ```python
   LOCAL_API_BASE = "http://windows_ip_address:5100"
   API_KEY = "your_api_key"
   ```

4. **Start the MCP server**:
   ```bash
   python visio_bridge_server.py
   ```

### 3. Configure Claude for Desktop

1. Edit the Claude Desktop configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the MCP server configuration:
   ```json
   {
     "mcpServers": {
       "visio-bridge": {
         "command": "python",
         "args": [
           "/absolute/path/to/mcp-server/visio_bridge_server.py"
         ]
       }
     }
   }
   ```

3. Restart Claude for Desktop

## Testing the Connection

1. Open Claude for Desktop
2. Ask Claude: "Can you check if my Visio connection is working?"
3. Claude should use the `check_visio_connection` tool and report the status

## Troubleshooting

### Connection Issues

- **API Key Error**: Make sure the API key on your Mac matches the one displayed on Windows
- **Network Connectivity**: Ensure both machines can reach each other (try pinging the Windows IP from Mac)
- **Firewall Issues**: Check if Windows Firewall is blocking port 5100
- **VPN Considerations**: If using a VPN, ensure it allows direct connections between devices

### Windows-Specific Issues

- **COM Errors**: Make sure Visio is installed and running on the Windows machine
- **Permission Issues**: Run the API server with administrator privileges if needed

### Mac-Specific Issues

- **Environment Variables**: Verify the environment variables are set correctly:
  ```bash
  echo $VISIO_BRIDGE_API_URL
  echo $VISIO_BRIDGE_API_KEY
  ```

## Security Considerations

This setup exposes your Visio API server to your local network. To enhance security:

1. **Use a Strong API Key**: The automatically generated key is secure, but you can set your own via the `VISIO_BRIDGE_API_KEY` environment variable
2. **Firewall Rules**: Configure the Windows firewall to only accept connections from your Mac's IP address
3. **VPN**: Consider using a VPN between your Mac and Windows machine for additional security
4. **HTTPS**: For production environments, consider setting up HTTPS with a self-signed certificate

## Permanent Configuration

To make your configuration permanent on your Mac:

1. Add the following to your `~/.bashrc` or `~/.zshrc`:
   ```bash
   export VISIO_BRIDGE_API_URL="http://windows_ip_address:5100"
   export VISIO_BRIDGE_API_KEY="your_api_key"
   ```

2. Reload your shell configuration:
   ```bash
   source ~/.bashrc  # or source ~/.zshrc
   ```
