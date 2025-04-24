# 🚀 Visio Bridge Integration Suite

<div align="center">

![Status](https://img.shields.io/badge/Status-Beta-yellow)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Node](https://img.shields.io/badge/Node.js-18+-339933?logo=nodedotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14+-black?logo=nextdotjs&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**A suite of tools to integrate Microsoft Visio with web content, AI assistants, and provide a modern search interface.**

[Key Features](#key-features) • [Installation](#installation) • [Usage](#usage) • [Documentation](#documentation)

</div>

---

## 📋 Overview

This project consists of four main components:

1.  **Next.js Frontend**: A modern web application providing a user interface for searching stencils/shapes, managing favorites and collections, and viewing system status. Built with Next.js, React, TypeScript, Shadcn/UI, and Tailwind CSS.
2.  **Chrome Extension**: Allows users to capture selected text or a region of their screen from any webpage and send it to Visio via the Local API Server.
3.  **Local API Server**: A Python (FastAPI) application running on the user's Windows machine that serves the frontend, interacts with the stencil database, and uses PyWin32 COM automation to insert content into the active Microsoft Visio document.
4.  **MCP Server**: A Model Context Protocol server that enables AI assistants like Claude to interact with Visio through the local API.

The goal is to streamline the process of finding Visio shapes, getting information from the web/AI assistants into Visio diagrams, and managing stencil assets effectively.

## ✨ Key Features

- ✨ **Modern Search UI**: Fast, responsive search interface built with Next.js and Shadcn/UI.
- ✨ **Real-time Shape Search**: Search across stencils with pagination and type-ahead suggestions (via debouncing).
- ✨ **Favorites & Collections**: Organize frequently used shapes and group related shapes.
- ✨ **Health & Settings**: Monitor backend status and trigger actions like rescanning stencils.
- ✨ **Responsive Design**: UI adapts for both desktop and mobile use (with drawer navigation).
- ✨ **Context Menu Integration**: Right-click selected text to send directly to Visio.
- ✨ **Region Screenshot Capture**: Click the extension popup button to select a screen region for capture.
- ✨ **Local API Bridge**: A lightweight FastAPI server listens locally for requests from the extension and frontend.
- ✨ **Visio COM Automation**: Uses PyWin32 on Windows to interact with the running Visio application (Optional).
- ✨ **Text & Image Insertion**: Inserts captured text or screenshots into the active Visio document (Requires Local API + Visio).
- ✨ **AI Assistant Integration**: MCP server allows AI assistants like Claude to interact with Visio.

## 💻 Installation

### Prerequisites

- Python 3.10 or higher
- Node.js 18.x or higher (for Next.js frontend)
- npm or yarn (Node.js package manager)
- Git (optional, for cloning)
- Microsoft Visio (optional, for COM automation features)
- Chrome browser (for extension)
- Claude for Desktop (optional, for AI assistant integration)

### Quick Install

### 1. Backend Components (Local API & MCP Server)

```bash
# --- Local API Server ---
cd local-api-server
python -m venv venv
# Activate venv (source venv/bin/activate or venv\Scripts\activate)
pip install -r requirements.txt

# --- MCP Server (Optional) ---
cd ../mcp-server
python -m venv venv
# Activate venv
pip install -r requirements.txt
```

### 2. Next.js Frontend

```bash
# Navigate to the frontend directory
cd next-frontend

# Install dependencies
npm install
# or
# yarn install
```

### 3. Chrome Extension

No build step required. Load directly into Chrome in developer mode.

## 🚀 Usage

### 1. Starting the Local API Server

```bash
cd local-api-server
# Activate venv if used
python main.py
```
The server will listen on `http://127.0.0.1:5100`.

### 2. Starting the Next.js Frontend (Development Mode)

```bash
cd next-frontend
npm run dev
# or
# yarn dev
```
The frontend will be accessible at `http://localhost:3000`.

### 3. Starting the MCP Server (Optional)

```bash
cd mcp-server
# Activate venv if used
python visio_bridge_server.py
```

### 4. Loading the Chrome Extension

1.  Open Chrome and navigate to `chrome://extensions/`.
2.  Enable "Developer mode".
3.  Click "Load unpacked".
4.  Select the `chrome-extension` directory.

### 5. Configuring Claude for Desktop (Optional)

1.  Edit the Claude Desktop configuration file:
    *   macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
    *   Windows: `%APPDATA%\Claude\claude_desktop_config.json`
2.  Add the MCP server configuration (ensure the path is correct):
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
3.  Restart Claude for Desktop.

### 6. Using the Tools

#### Next.js Frontend

1.  **Ensure the Local API Server is running.**
2.  Open your browser to `http://localhost:3000`.
3.  Use the Search page to find shapes.
4.  Manage Favorites and Collections.
5.  Check system status on the Health page.
6.  Trigger scans from the Settings page.

#### Chrome Extension

1.  **Ensure the Local API Server is running.**
2.  **Text Capture**: Select text, right-click, choose "Send selected text to Visio".
3.  **Screenshot Capture**: Click the extension icon, click "Capture Screenshot", draw a region, click "Send Content to Visio".

#### Claude for Desktop

1.  **Ensure both the Local API Server and MCP Server are running.**
2.  **Ask Claude**: Use natural language for Visio tasks (e.g., "Search for network shapes", "Import this text...").

## 🛠️ Troubleshooting

| Issue                      | Solution                                                                                     |
| :------------------------- | :------------------------------------------------------------------------------------------- |
| **Python not recognized**  | Ensure Python is installed and in your system PATH.                                          |
| **Node/npm not recognized** | Ensure Node.js (v18+) is installed and in your system PATH.                                  |
| **ModuleNotFoundError**    | Ensure virtual environments are activated and run `pip install` or `npm install` again.        |
| **Extension Errors**       | Check Chrome's extension console (`chrome://extensions/` -> Details -> Service Worker/Errors). |
| **API Server Errors**      | Check the terminal where `local-api-server` is running.                                      |
| **Frontend Errors**        | Check the browser's developer console and the terminal where `next-frontend` is running.   |
| **Connection Refused**     | Ensure the Local API Server is running on port 5100. Check CORS settings in `main.py`.     |
| **Visio COM Errors**       | Ensure Visio is installed and running (if using extension). Check API server console.        |
| **MCP Server Errors**      | Check `visio_bridge_mcp.log`.                                                                |
| **Claude Config Errors**   | Verify the path to `visio_bridge_server.py` in Claude's config.                              |

## 📁 Project Structure

```
streamlit-stencil-search/
├── next-frontend/        # Next.js Frontend UI
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
├── chrome-extension/     # Chrome Extension files
│   └── ...
├── local-api-server/     # Python FastAPI server (Backend for Frontend & Extension)
│   ├── main.py
│   ├── visio_integration.py
│   └── requirements.txt
├── mcp-server/           # MCP server for AI assistant integration
│   └── ...
├── app/                  # Core Python logic (Shared by local-api-server, potentially old Streamlit app)
│   ├── core/
│   └── data/
├── docs/                 # Documentation
│   └── ...
├── memory-bank/          # Project Memory / context files
│   └── ...
├── .gitignore
└── README.md             # This file
```

## 📜 Startup Scripts & Utility Tools

The project includes several helper scripts to streamline development and testing:

### Startup Scripts

#### `start_all.ps1` (PowerShell) 
The main startup script that launches all core components as background jobs:

```powershell
# Run from PowerShell in project root
.\start_all.ps1
```

This script:
- Starts the Local API Server (with automatic virtual environment activation)
- Starts the MCP Server
- Starts the Next.js Frontend in development mode
- Configures logging to separate log files for each component
- Runs everything as background jobs in a single PowerShell instance

**Tip:** Use `Get-Job` to check running job status and `Stop-Job -Name JOB_NAME` to stop specific jobs.

#### `start_inspector.bat` (Windows Batch)
Launches the MCP Inspector for debugging and testing the MCP server:

```batch
start_inspector.bat
```

This script:
- Starts the MCP Inspector tool (requires Node.js/npm)
- Connects to the MCP server to enable interactive testing
- Opens a web interface at http://localhost:6274
- Note: Requires the Local API Server to be running first

#### `start_streamlit.ps1` (PowerShell)
Attempts to start the legacy Streamlit UI:

```powershell
# Run from PowerShell in project root
.\start_streamlit.ps1
```

**Note:** This script launches the older Streamlit version of the UI (now replaced by Next.js). It may not function correctly with the current API server and should be used only for reference or legacy purposes.

### Root Python Scripts

#### `app.py`
The main entry point for the legacy Streamlit application:
- Configures the Streamlit UI with navigation and pages
- Initializes the database and checks integrity
- Sets up session state, error handling, and logging
- Injects custom CSS and JavaScript for improved UI
- Creates the tabbed interface for different app modules

**Usage:**
```bash
streamlit run app.py
```

#### `build.py`
Build script for creating distributable packages:
- Creates standalone executables using PyInstaller
- Builds Docker images for containerized deployment
- Supports multiple build targets (--exe, --docker, or --all)

**Usage:**
```bash
# Show help and options
python build.py

# Build executable only
python build.py --exe

# Build Docker image only
python build.py --docker

# Build both executable and Docker image
python build.py --all
```

#### `test_db.py`
Comprehensive test script for the stencil database functionality:
- Tests database connection and creation
- Verifies preset directories CRUD operations
- Tests stencil caching and retrieval
- Validates saved searches functionality
- Tests favorites system
- Benchmarks search performance (FTS vs. LIKE)

**Usage:**
```bash
python test_db.py
```

#### `test_favorites.py`
Targeted test script specifically for the favorites functionality:
- Tests adding stencils to favorites
- Verifies favorite status checking
- Tests retrieving all favorites
- Validates removing favorites
- Checks database integrity and foreign key constraints

**Usage:**
```bash
python test_favorites.py
```

## 📚 Documentation

- [Chrome Extension & API Bridge Architecture](docs/Chrome-Visio-Extension-Plan-Detailed.md)
- [MCP Server Documentation](docs/MCP-Server-Documentation.md)
- [MCP Server Quick Start Guide](docs/MCP-Server-QuickStart.md)
- [MCP Server Technical Architecture](docs/MCP-Server-Architecture.md)
- [Remote Visio Setup Guide](docs/Remote-Visio-Setup.md) - Use the MCP server on Mac with Visio on Windows

---

<div align="center">

  Made with ❤️ by Sam Lyndon

  © 2025
</div>
