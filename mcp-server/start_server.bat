@echo off
echo Starting Visio Bridge MCP Server...
echo.
echo Make sure the local Visio Bridge API is running on port 5100
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated.
) else (
    echo Warning: Virtual environment not found. Make sure dependencies are installed.
)

REM Start the server
python visio_bridge_server.py

REM If we get here, the server has stopped
echo.
echo Server has stopped. Press any key to exit...
pause > nul
