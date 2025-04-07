from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal
import uvicorn
import sys
import os # Added for potential path adjustments
# Import the Visio integration functions
import visio_integration

# Basic App Setup
app = FastAPI(
    title="Visio Integration Bridge API",
    description="Receives content from the Chrome extension and sends it to Visio via COM.",
    version="0.1.0"
)

# CORS Configuration
# Allow requests only from the extension's origin (when loaded)
# For development, might allow broader origins like localhost, but restrict in production.
# Example: Adjust origins as needed for development vs. packaged extension
origins = [
    # "chrome-extension://YOUR_EXTENSION_ID_HERE", # Replace with actual extension ID
    "http://localhost", # Example for local dev testing
    "http://127.0.0.1", # Example for local dev testing
    # Add other origins if needed for testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Restrict origins in production
    allow_credentials=True,
    allow_methods=["POST", "GET"], # Allow POST for import, GET for health check
    allow_headers=["*"],
)

# Visio Integration module is imported, no need for a stub here.

# --- Pydantic Models ---

class ImportMetadata(BaseModel):
    """ Optional metadata about the captured content. """
    source_url: Optional[str] = None
    capture_time: Optional[str] = None # Consider using datetime format later
    user_options: Optional[Dict] = {} # For future options like embed type

class ImportPayload(BaseModel):
    """ Defines the structure of the data sent from the Chrome extension. """
    type: Literal['text', 'image'] = Field(..., description="The type of content being sent.")
    content: str = Field(..., description="The actual content (plain text or Base64 encoded image string).")
    metadata: Optional[ImportMetadata] = None

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """ Basic health check endpoint. """
    return {"message": "Visio Integration Bridge API is running"}

@app.post("/import")
async def import_content(payload: ImportPayload):
    """
    Receives content (text or image) from the Chrome extension
    and passes it to the Visio integration module.
    """
    print(f"Received import request: Type='{payload.type}', Metadata='{payload.metadata}'")
    try:
        if payload.type == "text":
            result = visio_integration.import_text_to_visio(payload.content, payload.metadata)
        elif payload.type == "image":
            # Basic validation: Check if content looks like Base64 (can be improved)
            if not payload.content.startswith('data:image'):
                 print(f"Warning: Received image content doesn't start with 'data:image...' - {payload.content[:60]}...")
            result = visio_integration.import_image_to_visio(payload.content, payload.metadata)
        else:
            # Should not happen due to Pydantic validation, but good practice
            raise HTTPException(status_code=400, detail="Invalid content type specified.")

        # Check stub/integration result
        if result.get("status") == "success":
            return result
        else:
            # Pass potential errors from the integration layer
            error_detail = result.get("message", "Integration failed")
            print(f"Error during Visio integration: {error_detail}")
            raise HTTPException(status_code=500, detail=f"Visio integration failed: {error_detail}")

    except visio_integration.VisioIntegrationError as vie:
         # Catch specific integration errors (e.g., connection failed)
         print(f"VisioIntegrationError in /import: {vie}", file=sys.stderr)
         raise HTTPException(status_code=503, detail=f"Visio integration error: {vie}") # 503 Service Unavailable might fit
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions from validation or logic
        raise http_exc
    except Exception as e:
        # Catch-all for other unexpected errors during processing
        print(f"Unexpected error processing /import: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # Default port, can be made configurable later
    port = 5100 # Align with port in manifest.json host_permissions
    print(f"Starting Visio Integration Bridge API on http://127.0.0.1:{port}")

    # Check if running as a packaged executable (e.g., PyInstaller)
    # Required for PyWin32 COM access when run from a frozen environment
    if getattr(sys, 'frozen', False):
        # If frozen, CWD might be different, ensure pywintypes are accessible
        # This might require specific PyInstaller hooks or path adjustments
        print("Running as a packaged executable.")
        # Add potential path adjustments if needed for pywintypesXX.dll
        # Example path adjustment logic (adapt as needed based on PyInstaller setup)
        if hasattr(sys, '_MEIPASS'):
           # Add the directory containing the executable to PATH
           # This might help find DLLs like pywintypesXX.dll if they are bundled alongside
           _path = os.environ.get("PATH", "")
           _meipass = getattr(sys, '_MEIPASS')
           if _meipass not in _path:
               os.environ['PATH'] = _meipass + os.pathsep + _path
               print(f"Adjusted PATH for PyInstaller: {os.environ['PATH']}")

    uvicorn.run(app, host="127.0.0.1", port=port)