# start_all.ps1
# Script to start all components of the Visio Bridge Integration Suite sequentially

$delaySeconds = 5 # Adjust delay if needed

Write-Host "Starting Local API Server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { Push-Location local-api-server; .\venv\Scripts\Activate.ps1; python main.py; Pop-Location }" -WorkingDirectory $PSScriptRoot

Write-Host "Waiting $delaySeconds seconds for Local API Server to initialize..."
Start-Sleep -Seconds $delaySeconds

Write-Host "Starting MCP Server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { Push-Location mcp-server; .\venv\Scripts\Activate.ps1; python visio_bridge_server.py; Pop-Location }" -WorkingDirectory $PSScriptRoot

Write-Host "Waiting $delaySeconds seconds for MCP Server to initialize..."
Start-Sleep -Seconds $delaySeconds

Write-Host "Starting Next.js Frontend (Development Mode)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { Push-Location next-frontend; npm run dev; Pop-Location }" -WorkingDirectory $PSScriptRoot

Write-Host "All components are starting sequentially in separate windows." 