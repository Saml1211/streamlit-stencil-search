@echo off
REM Batch file to start the MCP Inspector for the Visio Bridge server.

REM Ensure you are in the project's root directory before running this script.
REM Also ensure the Local API server (local_api_server.py) is running.

echo Starting MCP Inspector for Visio Bridge...
echo Make sure the Local API Server is running at http://127.0.0.1:8001

REM --- Configuration ---
set PYTHON_EXE=venv\\Scripts\\python.exe
set MCP_SCRIPT=visio_bridge/mcp_server.py
set API_URL=http://127.0.0.1:8001
REM -------------------

REM Check if npx requires installation confirmation (it shouldn't after the first time)
REM The command launches the inspector and passes the Python script and its arguments.
npx @modelcontextprotocol/inspector -- %PYTHON_EXE% %MCP_SCRIPT% --api-url %API_URL%

echo MCP Inspector process initiated. Check your terminal for output.
echo UI should be available at http://localhost:6274 (default).

pause 