#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup script for Visio Bridge Integration Suite
.DESCRIPTION
    A comprehensive setup script for the Visio Bridge Integration Suite that automates
    configuration and installation of all components including:
    - Local API Server
    - MCP Server
    - Next.js Frontend
    - Environment validation
    - Configuration setup
.NOTES
    Author: Automated Setup
    Version: 1.0
#>

# Script configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"
$HOST.UI.RawUI.BackgroundColor = "Black"
$HOST.UI.RawUI.ForegroundColor = "White"
Clear-Host

# ===== Helper Functions =====

function Write-ColorText {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text,
        
        [Parameter(Mandatory=$true)]
        [ValidateSet("Black", "DarkBlue", "DarkGreen", "DarkCyan", "DarkRed", "DarkMagenta", "DarkYellow", "Gray", "DarkGray", "Blue", "Green", "Cyan", "Red", "Magenta", "Yellow", "White")]
        [string]$ForegroundColor,
        
        [Parameter(Mandatory=$false)]
        [switch]$NoNewLine
    )
    
    $originalColor = $HOST.UI.RawUI.ForegroundColor
    $HOST.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($NoNewLine) {
        Write-Host -NoNewline $Text
    } else {
        Write-Host $Text
    }
    $HOST.UI.RawUI.ForegroundColor = $originalColor
}

function Write-Header {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text
    )
    
    Write-Host ""
    Write-ColorText -Text "=============================================================="-ForegroundColor Cyan
    Write-ColorText -Text "  $Text" -ForegroundColor Cyan
    Write-ColorText -Text "==============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text
    )
    
    Write-ColorText -Text "✓ $Text" -ForegroundColor Green
}

function Write-Error {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text,
        
        [Parameter(Mandatory=$false)]
        [string]$Details = "",
        
        [Parameter(Mandatory=$false)]
        [switch]$Fatal
    )
    
    Write-ColorText -Text "✗ ERROR: $Text" -ForegroundColor Red
    if ($Details) {
        Write-ColorText -Text "  $Details" -ForegroundColor DarkGray
    }
    
    if ($Fatal) {
        Write-ColorText -Text "  This error requires attention before setup can continue." -ForegroundColor Red
        Write-ColorText -Text "  Please resolve the issue and run the setup script again." -ForegroundColor Red
        exit 1
    }
}

function Write-Warning {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text
    )
    
    Write-ColorText -Text "! WARNING: $Text" -ForegroundColor Yellow
}

function Write-Info {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text
    )
    
    Write-ColorText -Text "ℹ $Text" -ForegroundColor Blue
}

function Write-Step {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Text
    )
    
    Write-ColorText -Text "→ $Text" -ForegroundColor White
}

function Test-CommandExists {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Get-CommandVersion {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command,
        
        [Parameter(Mandatory=$true)]
        [string]$VersionParam
    )
    
    try {
        $versionOutput = (Invoke-Expression -Command "$Command $VersionParam") 2>&1
        
        # Node.js outputs version with a leading 'v' (e.g., 'v22.14.0')
        if ($versionOutput -match 'v(\d+\.\d+\.\d+)') {
            return $Matches[1]
        } elseif ($versionOutput -match '(\d+\.\d+\.\d+)') {
            return $Matches[1]
        } elseif ($versionOutput -match 'v(\d+\.\d+)') {
            return $Matches[1]
        } elseif ($versionOutput -match '(\d+\.\d+)') {
            return $Matches[1]
        } else {
            Write-Warning "Could not parse version information from: $versionOutput"
            return "Unknown"
        }
    } catch {
        Write-Warning "Error getting version: $($_.Exception.Message)"
        return "Error"
    }
}

function Compare-Version {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Version,
        
        [Parameter(Mandatory=$true)]
        [string]$MinimumVersion
    )
    
    try {
        # Clean version strings - remove leading 'v' if present
        $cleanVersion = $Version -replace '^v', ''
        $cleanMinVersion = $MinimumVersion -replace '^v', ''
        
        # Handle simple major version comparison if needed
        if ($cleanMinVersion -match '^\d+$') {
            $majorVersion = $cleanVersion -replace '^(\d+).*', '$1'
            return [int]$majorVersion -ge [int]$cleanMinVersion
        }
        
        # Otherwise do normal version comparison
        $versionObj = [Version]::new($cleanVersion)
        $minVersionObj = [Version]::new($cleanMinVersion)
        
        return $versionObj -ge $minVersionObj
    } catch {
        Write-Warning "Version comparison error: $($_.Exception.Message)"
        # Fallback to string comparison if version parsing fails
        return $Version -ge $MinimumVersion
    }
}

function Create-VirtualEnv {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Directory,
        
        [Parameter(Mandatory=$true)]
        [string]$EnvName
    )
    
    try {
        $envPath = Join-Path -Path $Directory -ChildPath $EnvName
        
        if (Test-Path $envPath) {
            Write-Info "Virtual environment already exists at $envPath"
            return $true
        }
        
        Push-Location $Directory
        Write-Step "Creating virtual environment in $Directory..."
        python -m venv $EnvName
        if (-not (Test-Path $envPath)) {
            Write-Error "Failed to create virtual environment" -Details "Check Python installation and permissions"
            Pop-Location
            return $false
        }
        Write-Success "Created virtual environment: $EnvName"
        Pop-Location
        return $true
    } catch {
        Write-Error "Failed to create virtual environment" -Details $_.Exception.Message
        if ($Directory -ne (Get-Location).Path) {
            Pop-Location
        }
        return $false
    }
}

function Install-Requirements {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Directory,
        
        [Parameter(Mandatory=$true)]
        [string]$EnvName,
        
        [Parameter(Mandatory=$true)]
        [string]$RequirementsFile
    )
    
    try {
        Push-Location $Directory
        $activateScript = Join-Path -Path $EnvName -ChildPath "Scripts\Activate.ps1"
        
        if (-not (Test-Path $activateScript)) {
            Write-Error "Activation script not found" -Details "Expected at: $activateScript"
            Pop-Location
            return $false
        }
        
        Write-Step "Installing requirements from $RequirementsFile..."
        
        # Create a temporary script to activate venv and install requirements
        $tempScriptPath = [System.IO.Path]::GetTempFileName() + ".ps1"
        @"
. '$activateScript'
pip install -r '$RequirementsFile'
"@ | Out-File -FilePath $tempScriptPath
        
        # Execute the temporary script
        $output = & pwsh -NoProfile -ExecutionPolicy Bypass -File $tempScriptPath
        $success = $LASTEXITCODE -eq 0
        
        # Clean up the temporary script
        Remove-Item -Path $tempScriptPath -Force
        
        if (-not $success) {
            Write-Error "Failed to install requirements" -Details "pip exited with error code $LASTEXITCODE"
            Pop-Location
            return $false
        }
        
        Write-Success "Installed all requirements from $RequirementsFile"
        Pop-Location
        return $true
    } catch {
        Write-Error "Failed to install requirements" -Details $_.Exception.Message
        if ($Directory -ne (Get-Location).Path) {
            Pop-Location
        }
        return $false
    }
}

function Install-NpmDependencies {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Directory
    )
    
    try {
        Push-Location $Directory
        Write-Step "Installing NPM dependencies in $Directory..."
        
        $output = npm install
        $success = $LASTEXITCODE -eq 0
        
        if (-not $success) {
            Write-Error "Failed to install NPM dependencies" -Details "npm exited with error code $LASTEXITCODE"
            Pop-Location
            return $false
        }
        
        Write-Success "Installed all NPM dependencies"
        Pop-Location
        return $true
    } catch {
        Write-Error "Failed to install NPM dependencies" -Details $_.Exception.Message
        if ($Directory -ne (Get-Location).Path) {
            Pop-Location
        }
        return $false
    }
}

function Test-Port {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port
    )
    
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

function Test-FilePermission {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        
        [Parameter(Mandatory=$true)]
        [string]$Permission
    )
    
    try {
        $item = Get-Item -Path $Path -ErrorAction Stop
        $acl = Get-Acl -Path $item.FullName
        
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
        
        $rights = "FullControl"
        Switch($Permission) {
            "Read" { $rights = "ReadAndExecute" }
            "Write" { $rights = "Write" }
            "Execute" { $rights = "ExecuteFile" }
            "Full" { $rights = "FullControl" }
        }
        
        foreach ($accessRule in $acl.Access) {
            $identityReference = $accessRule.IdentityReference
            if ($principal.IsInRole($identityReference)) {
                if ($accessRule.FileSystemRights -band [System.Security.AccessControl.FileSystemRights]::$rights) {
                    return $true
                }
            }
        }
        
        return $false
    } catch {
        return $false
    }
}

# ===== Environment Validation Functions =====

function Test-PythonEnvironment {
    Write-Header "Checking Python Environment"
    
    if (-not (Test-CommandExists -Command "python")) {
        Write-Error "Python not found" -Details "Python 3.10+ is required. Please install Python and ensure it's in your PATH." -Fatal
        return $false
    }
    
    $pythonVersion = Get-CommandVersion -Command "python" -VersionParam "--version"
    Write-Info "Found Python version $pythonVersion"
    
    if (-not (Compare-Version -Version $pythonVersion -MinimumVersion "3.10")) {
        Write-Error "Python version requirement not met" -Details "Found $pythonVersion, but 3.10+ is required." -Fatal
        return $false
    }
    
    if (-not (Test-CommandExists -Command "pip")) {
        Write-Error "pip not found" -Details "pip is required to install Python dependencies." -Fatal
        return $false
    }
    
    Write-Success "Python environment validated successfully"
    return $true
}

function Test-NodeEnvironment {
    Write-Header "Checking Node.js Environment"
    
    if (-not (Test-CommandExists -Command "node")) {
        Write-Error "Node.js not found" -Details "Node.js 18+ is required. Please install Node.js and ensure it's in your PATH." -Fatal
        return $false
    }
    
    $nodeVersion = Get-CommandVersion -Command "node" -VersionParam "--version"
    Write-Info "Found Node.js version $nodeVersion"
    
    if (-not (Compare-Version -Version $nodeVersion -MinimumVersion "18")) {
        Write-Error "Node.js version requirement not met" -Details "Found $nodeVersion, but version 18 or higher is required." -Fatal
        return $false
    }
    
    if (-not (Test-CommandExists -Command "npm")) {
        Write-Error "npm not found" -Details "npm is required to install Node.js dependencies." -Fatal
        return $false
    }
    
    Write-Success "Node.js environment validated successfully"
    return $true
}

function Test-SystemRequirements {
    Write-Header "Checking System Requirements"
    
    # Check ports
    $requiredPorts = @(5100, 5101, 3000)
    $unavailablePorts = @()
    
    foreach ($port in $requiredPorts) {
        if (-not (Test-Port -Port $port)) {
            $unavailablePorts += $port
        }
    }
    
    if ($unavailablePorts.Count -gt 0) {
        Write-Warning "The following ports are in use and may cause conflicts: $($unavailablePorts -join ', ')"
        Write-Warning "Applications using these ports must be stopped before running the system."
    } else {
        Write-Success "All required ports are available"
    }
    
    # Check disk space
    $requiredSpaceMB = 500
    $drive = (Get-Location).Drive
    $freeSpaceMB = [math]::Round((Get-PSDrive -Name $drive.Name).Free / 1MB)
    
    if ($freeSpaceMB -lt $requiredSpaceMB) {
        Write-Error "Insufficient disk space" -Details "Found $freeSpaceMB MB, but $requiredSpaceMB MB is required." -Fatal
        return $false
    } else {
        Write-Success "Sufficient disk space available ($freeSpaceMB MB free)"
    }
    
    # Check file permissions
    $workingDir = Get-Location
    if (-not (Test-FilePermission -Path $workingDir -Permission "Write")) {
        Write-Error "Insufficient file permissions" -Details "Write permission is required for the project directory." -Fatal
        return $false
    } else {
        Write-Success "File permissions verified for the project directory"
    }
    
    # Check Visio (optional)
    $hasVisio = $false
    try {
        $visioCheck = Get-WmiObject Win32_Product | Where-Object { $_.Name -like "*Visio*" }
        if ($visioCheck) {
            $hasVisio = $true
            Write-Success "Microsoft Visio is installed (COM automation features will be available)"
        } else {
            Write-Warning "Microsoft Visio not detected (COM automation features will be limited)"
        }
    } catch {
        Write-Warning "Could not verify Microsoft Visio installation (skipping)"
    }
    
    return $true
}

# ===== Component Setup Functions =====

function Setup-LocalAPIServer {
    Write-Header "Setting up Local API Server"
    
    $apiServerDir = Join-Path -Path (Get-Location) -ChildPath "local-api-server"
    if (-not (Test-Path $apiServerDir)) {
        Write-Error "Local API Server directory not found" -Details "Expected at: $apiServerDir" -Fatal
        return $false
    }
    
    if (-not (Create-VirtualEnv -Directory $apiServerDir -EnvName "venv")) {
        return $false
    }
    
    $requirementsFile = Join-Path -Path $apiServerDir -ChildPath "requirements.txt"
    if (-not (Test-Path $requirementsFile)) {
        Write-Error "Requirements file not found" -Details "Expected at: $requirementsFile" -Fatal
        return $false
    }
    
    if (-not (Install-Requirements -Directory $apiServerDir -EnvName "venv" -RequirementsFile "requirements.txt")) {
        return $false
    }
    
    Write-Success "Local API Server setup completed successfully"
    return $true
}

function Setup-MCPServer {
    Write-Header "Setting up MCP Server"
    
    $mcpServerDir = Join-Path -Path (Get-Location) -ChildPath "mcp-server"
    if (-not (Test-Path $mcpServerDir)) {
        Write-Error "MCP Server directory not found" -Details "Expected at: $mcpServerDir" -Fatal
        return $false
    }
    
    if (-not (Create-VirtualEnv -Directory $mcpServerDir -EnvName "venv")) {
        return $false
    }
    
    $requirementsFile = Join-Path -Path $mcpServerDir -ChildPath "requirements.txt"
    if (-not (Test-Path $requirementsFile)) {
        Write-Error "Requirements file not found" -Details "Expected at: $requirementsFile" -Fatal
        return $false
    }
    
    if (-not (Install-Requirements -Directory $mcpServerDir -EnvName "venv" -RequirementsFile "requirements.txt")) {
        return $false
    }
    
    # Setup Claude Desktop config example if needed
    $claudeConfigDir = Join-Path -Path $env:APPDATA -ChildPath "Claude"
    $claudeConfigFile = Join-Path -Path $claudeConfigDir -ChildPath "claude_desktop_config.json"
    $exampleConfigFile = Join-Path -Path $mcpServerDir -ChildPath "claude_desktop_config_example.json"
    
    if (Test-Path $exampleConfigFile) {
        Write-Info "Example Claude Desktop configuration available at: $exampleConfigFile"
        Write-Info "To enable Claude integration, you can adapt this configuration to your local setup"
        
        if (Test-Path $claudeConfigFile) {
            Write-Info "Existing Claude Desktop configuration found at: $claudeConfigFile"
        } else {
            Write-Info "Claude Desktop configuration should be placed at: $claudeConfigFile"
        }
    }
    
    Write-Success "MCP Server setup completed successfully"
    return $true
}

function Setup-NextFrontend {
    Write-Header "Setting up Next.js Frontend"
    
    $frontendDir = Join-Path -Path (Get-Location) -ChildPath "next-frontend"
    if (-not (Test-Path $frontendDir)) {
        Write-Error "Next.js Frontend directory not found" -Details "Expected at: $frontendDir" -Fatal
        return $false
    }
    
    if (-not (Install-NpmDependencies -Directory $frontendDir)) {
        return $false
    }
    
    Write-Success "Next.js Frontend setup completed successfully"
    return $true
}

function Setup-ChromeExtension {
    Write-Header "Setting up Chrome Extension"
    
    $extensionDir = Join-Path -Path (Get-Location) -ChildPath "chrome-extension"
    if (-not (Test-Path $extensionDir)) {
        Write-Error "Chrome Extension directory not found" -Details "Expected at: $extensionDir" -Fatal
        return $false
    }
    
    $manifestFile = Join-Path -Path $extensionDir -ChildPath "manifest.json"
    if (-not (Test-Path $manifestFile)) {
        Write-Error "Extension manifest file not found" -Details "Expected at: $manifestFile" -Fatal
        return $false
    }
    
    Write-Success "Chrome Extension is ready for loading in developer mode"
    Write-Info "To install the extension in Chrome:"
    Write-Info "  1. Open Chrome and navigate to chrome://extensions/"
    Write-Info "  2. Enable 'Developer mode'"
    Write-Info "  3. Click 'Load unpacked'"
    Write-Info "  4. Select the chrome-extension directory: $extensionDir"
    
    return $true
}

# ===== Main Setup Logic =====

function Show-Banner {
    Clear-Host
    Write-Host ""
    Write-ColorText -Text "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-ColorText -Text "║                                                           ║" -ForegroundColor Cyan
    Write-ColorText -Text "║   " -ForegroundColor Cyan -NoNewLine
    Write-ColorText -Text "Visio Bridge Integration Suite - Setup Script" -ForegroundColor Yellow -NoNewLine
    Write-ColorText -Text "    ║" -ForegroundColor Cyan
    Write-ColorText -Text "║                                                           ║" -ForegroundColor Cyan
    Write-ColorText -Text "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Info "This script will set up all components of the Visio Bridge Integration Suite:"
    Write-Info "  • Local API Server (FastAPI, Python)"
    Write-Info "  • MCP Server (Optional, for AI assistant integration)"
    Write-Info "  • Next.js Frontend (React, TypeScript)"
    Write-Info "  • Chrome Extension (for web content capture)"
    Write-Host ""
    Write-ColorText -Text "This setup process includes:" -ForegroundColor White
    Write-ColorText -Text "  • Environment validation" -ForegroundColor White
    Write-ColorText -Text "  • Dependency installation" -ForegroundColor White
    Write-ColorText -Text "  • Virtual environment creation" -ForegroundColor White
    Write-ColorText -Text "  • Configuration setup" -ForegroundColor White
    Write-Host ""
}

function Show-Completion {
    param(
        [Parameter(Mandatory=$true)]
        [bool]$Success,
        
        [Parameter(Mandatory=$false)]
        [string[]]$FailedComponents = @()
    )
    
    if ($Success) {
        Write-Header "Setup Completed Successfully"
        Write-ColorText -Text "All components have been successfully set up." -ForegroundColor Green
        Write-Host ""
        Write-Info "To start the system:"
        Write-Info "  1. Local API Server: cd local-api-server; .\venv\Scripts\Activate.ps1; python main.py"
        Write-Info "  2. MCP Server (optional): cd mcp-server; .\venv\Scripts\Activate.ps1; python visio_bridge_server.py"
        Write-Info "  3. Next.js Frontend: cd next-frontend; npm run dev"
        Write-Info "  4. Chrome Extension: Load in Chrome developer mode"
        Write-Host ""
        Write-Info "For convenience, you can use the included start scripts:"
        Write-Info "  • start_all.ps1: Starts all components as background jobs"
        Write-Host ""
        Write-ColorText -Text "Thank you for setting up the Visio Bridge Integration Suite!" -ForegroundColor Green
    } else {
        Write-Header "Setup Completed with Errors"
        Write-ColorText -Text "The following components had setup errors:" -ForegroundColor Red
        foreach ($component in $FailedComponents) {
            Write-ColorText -Text "  • $component" -ForegroundColor Red
        }
        Write-Host ""
        Write-Info "Please fix the reported errors and run the setup script again."
        Write-Info "If you continue to encounter issues, check the troubleshooting section in README.md"
    }
}

# ===== Script Entry Point =====

# Show banner
Show-Banner

# Ask for confirmation
Write-Host ""
$confirmSetup = Read-Host "Do you want to proceed with the setup? (Y/N)"
if ($confirmSetup -notmatch "^[Yy]") {
    Write-ColorText -Text "Setup cancelled by user. Exiting..." -ForegroundColor Yellow
    exit 0
}

# Initialize tracking variables
$setupSuccess = $true
$failedComponents = @()

# Run environment validation
$envValid = $true
$envValid = $envValid -and (Test-PythonEnvironment)
$envValid = $envValid -and (Test-NodeEnvironment)
$envValid = $envValid -and (Test-SystemRequirements)

if (-not $envValid) {
    $setupSuccess = $false
    $failedComponents += "Environment Validation"
    Write-Error "Environment validation failed, cannot proceed with setup." -Fatal
}

# Setup Local API Server
if (-not (Setup-LocalAPIServer)) {
    $setupSuccess = $false
    $failedComponents += "Local API Server"
}

# Setup MCP Server
if (-not (Setup-MCPServer)) {
    $setupSuccess = $false
    $failedComponents += "MCP Server"
}

# Setup Next.js Frontend
if (-not (Setup-NextFrontend)) {
    $setupSuccess = $false
    $failedComponents += "Next.js Frontend"
}

# Setup Chrome Extension
if (-not (Setup-ChromeExtension)) {
    $setupSuccess = $false
    $failedComponents += "Chrome Extension"
}

# Show completion message
Show-Completion -Success $setupSuccess -FailedComponents $failedComponents

# Return appropriate exit code
if ($setupSuccess) {
    exit 0
} else {
    exit 1
} 