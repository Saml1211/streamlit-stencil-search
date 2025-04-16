# start_all.ps1
# Script to start all components of the Visio Bridge Integration Suite as background jobs
# Output will be logged to files in respective directories.

$delaySeconds = 5 # Adjust delay if needed

# Define Log Paths
$localApiLog = Join-Path $PSScriptRoot "local-api-server\local-api.log"
$mcpServerLog = Join-Path $PSScriptRoot "mcp-server\mcp-server.log"
$frontendLog = Join-Path $PSScriptRoot "next-frontend\next-frontend.log"

Write-Host "Starting Local API Server as a background job (logging to $localApiLog)..."
$localApiJob = Start-Job -ScriptBlock { 
    param($logPath)
    Push-Location local-api-server; 
    .\venv\Scripts\Activate.ps1; 
    python main.py *> $logPath;
    Pop-Location 
} -ArgumentList $localApiLog -WorkingDirectory $PSScriptRoot

Write-Host "Waiting $delaySeconds seconds for Local API Server to initialize..."
Start-Sleep -Seconds $delaySeconds

Write-Host "Starting MCP Server as a background job (logging to $mcpServerLog)..."
$mcpServerJob = Start-Job -ScriptBlock { 
    param($logPath)
    Push-Location mcp-server; 
    .\venv\Scripts\Activate.ps1; 
    python visio_bridge_server.py *> $logPath;
    Pop-Location 
} -ArgumentList $mcpServerLog -WorkingDirectory $PSScriptRoot

Write-Host "Waiting $delaySeconds seconds for MCP Server to initialize..."
Start-Sleep -Seconds $delaySeconds

Write-Host "Starting Next.js Frontend (Development Mode) as a background job (logging to $frontendLog)..."
$frontendJob = Start-Job -ScriptBlock { 
    param($logPath)
    Push-Location next-frontend; 
    npm run dev *> $logPath;
    Pop-Location 
} -ArgumentList $frontendLog -WorkingDirectory $PSScriptRoot

Write-Host "All components are starting as background jobs in this terminal."
Write-Host "Output is being redirected to log files."
Write-Host "Use 'Get-Job' to see job status."
Write-Host "To view logs, check the .log files in each component's directory or ask me to read them."
Write-Host "To stop a job, use 'Stop-Job -Name JOB_NAME'." 