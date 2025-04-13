# start_streamlit.ps1
# Script to ATTEMPT to start the OLD Streamlit UI

# --- IMPORTANT ---
# This script assumes the main Streamlit entry point is 'app.py' in the project root.
# It uses the local-api-server's virtual environment, which might be missing dependencies
# specific to the old Streamlit app. This UI is likely outdated and will NOT interact
# with the current FastAPI backend.
# ---

Write-Host "Attempting to start the old Streamlit UI..."
Write-Host "Using virtual environment from 'local-api-server'..."
Write-Host "Assuming entry point is 'app.py' in the root directory..."

# Start PowerShell, activate the API server's venv, navigate back to root, run streamlit
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { Push-Location local-api-server; .\venv\Scripts\Activate.ps1; Pop-Location; streamlit run app.py }" -WorkingDirectory $PSScriptRoot

Write-Host "Streamlit UI is attempting to start in a separate window."
Write-Host "Check that window for errors. It may not function correctly." 