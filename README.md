# 🚀 Chrome Extension to Visio Bridge

<div align="center">

![Status](https://img.shields.io/badge/Status-Beta-yellow)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29.0+-red?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**A Chrome extension and local API bridge to send web content (text, screenshots) directly into Microsoft Visio.**

[Key Features](#key-features) • [Installation](#installation) • [Usage](#usage) • [Documentation](#documentation)

</div>

---

## 📋 Overview

This project consists of two main components:
1.  **Chrome Extension**: Allows users to capture selected text or a region of their screen from any webpage.
2.  **Local API Server**: A Python (FastAPI) application running on the user's Windows machine that receives data from the extension and uses PyWin32 COM automation to insert it into the active Microsoft Visio document.

The goal is to streamline the process of getting information from the web into Visio diagrams.

## ✨ Key Features

- ✨ **Context Menu Integration**: Right-click selected text to send directly to Visio.
- ✨ **Region Screenshot Capture**: Click the extension popup button to select a screen region for capture.
- ✨ **Local API Bridge**: A lightweight FastAPI server listens locally for requests from the extension.
- ✨ **Visio COM Automation**: Uses PyWin32 on Windows to interact with the running Visio application (requires Visio installation).
- ✨ **Text & Image Insertion**: Inserts captured text or screenshots into the active Visio document (Implementation in `visio_integration.py` is ongoing).

## 💻 Installation

### Prerequisites

- Python 3.8 or higher
- Git (optional, for cloning)

### Quick Install

### Local API Server

```bash
# Navigate to the API server directory
cd local-api-server

# Create a virtual environment (optional but recommended)
# python -m venv venv
# source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

### Chrome Extension

No build step required for the current basic setup. The extension can be loaded directly into Chrome in developer mode.

*Note: Detailed installation instructions for packaging (PyInstaller for server, Zipping extension) will be added later.*

## 🚀 Usage

### Starting the Local API Server

*(Requires Python and installed dependencies from `local-api-server/requirements.txt`)*

```bash
cd local-api-server
uvicorn main:app --host 127.0.0.1 --port 5100 --reload
# Use --reload for development, remove for production/packaging
```
The server will listen on `http://127.0.0.1:5100`.

### Loading the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`.
2. Enable "Developer mode" (usually a toggle in the top right).
3. Click "Load unpacked".
4. Select the `chrome-extension` directory within this project.
5. The "Visio Content Importer" extension should appear and be active.

### Using the Extension

1.  **Ensure the Local API Server is running.**
2.  **Text Capture**: Select text on any webpage, right-click, and choose "Send selected text to Visio".
3.  **Screenshot Capture**: Click the extension's icon in the Chrome toolbar to open the popup. Click "Capture Screenshot", draw a rectangle on the page, and click "Send Content to Visio" in the popup (which reappears after capture).
4.  *(Note: Actual insertion into Visio requires completing the PyWin32 implementation in `visio_integration.py`).*

The application will open in your default web browser at `http://localhost:8501`

*This section is no longer relevant to the current project focus.*

<details>
*This section is not applicable as the API server is designed for localhost communication only.*

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| **Python not recognized** | Ensure Python is properly installed and added to your PATH |
| **ModuleNotFoundError** | Try reinstalling with `pip install -r requirements.txt` |
| **Port already in use** | If port 8501 is in use, Streamlit will try the next port |
| **Extension Errors** | Check Chrome's extension console (`chrome://extensions/` -> Details -> Service Worker / Errors) |
| **API Server Errors** | Check the terminal where the `uvicorn` command is running for logs and tracebacks. |
| **Connection Refused** | Ensure the Local API Server is running and listening on the correct port (default 5100). Check firewall settings if necessary. |
| **Visio COM Errors** | Ensure Visio is installed and running. Check error messages in the API server console. May require running the server with specific permissions. |

## 📁 Project Structure

```
streamlit-stencil-search/
├── chrome-extension/     # Chrome Extension files
│   ├── manifest.json
│   ├── background.js       # Service Worker
│   ├── popup.html
│   ├── popup.js
│   ├── content.js          # For text selection interaction
│   ├── region_selector.js  # For screenshot region selection UI
│   └── icons/              # Extension icons (16, 48, 128)
│
├── local-api-server/     # Python FastAPI server
│   ├── main.py             # FastAPI application
│   ├── visio_integration.py # Visio COM interaction logic (stub currently)
│   └── requirements.txt    # Python dependencies
│
├── docs/                 # Documentation
│   ├── Chrome-Visio-Extension-Plan.md         # Original high-level plan
│   └── Chrome-Visio-Extension-Plan-Detailed.md # Detailed architecture
│
├── memory-bank/          # Project Memory / Roo context files
│   ├── ... (standard memory bank files)
│
├── .gitignore
├── .roomodes             # Custom mode definitions
├── .roorules             # Project-specific rules/intelligence
└── README.md             # This file
```

## 📚 Documentation

For detailed technical architecture, see [Chrome-Visio-Extension-Plan-Detailed.md](docs/Chrome-Visio-Extension-Plan-Detailed.md).

---

<div align="center">

  Made with ❤️ by Sam Lyndon

  © 2025
</div>