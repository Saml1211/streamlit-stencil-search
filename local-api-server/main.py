from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal, List, Any
import uvicorn
import sys
import os
from pathlib import Path
import urllib.parse
import sqlite3 # Import for catching DB specific errors
from datetime import datetime # Needed for stub data
import secrets # For generating API key

# --- Add project root to sys.path to allow importing from 'app' ---
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# ---

# Import the Visio integration and DB functions
import visio_integration
from app.core.db import StencilDatabase
from app.core import file_scanner # Import the scanner module
import traceback # For detailed error logging

# Initialize DB instance (consider making path configurable)
db_path = project_root / "app" / "data" / "stencil_cache.db"
db = StencilDatabase(db_path=str(db_path))

# API Key Authentication Setup
# Generate a random API key if not already set in environment variables
API_KEY = os.environ.get("VISIO_BRIDGE_API_KEY", secrets.token_urlsafe(32))
api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Basic App Setup
app = FastAPI(
    title="Visio Integration Bridge API",
    description="Receives content from the Chrome extension and sends it to Visio via COM.",
    version="0.1.0"
)

# CORS Configuration
origins = [
    # "chrome-extension://YOUR_EXTENSION_ID_HERE", # Replace with actual extension ID
    "http://localhost:3000", # Allow Next.js dev server
    "http://localhost",
    "http://127.0.0.1",
    "*",  # Allow all origins when using API key authentication
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Adjust for production
    allow_credentials=True,
    # Allow GET, POST, PUT, DELETE for CRUD operations
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# --- Pydantic Models (Backend API) ---

class ShapeSummary(BaseModel):
    shape_id: int
    shape_name: str
    stencil_name: str
    stencil_path: str

class SearchResponse(BaseModel):
    results: List[ShapeSummary]
    total: int
    page: int
    size: int

class StencilSummary(BaseModel):
    path: str
    name: str
    extension: str
    shape_count: int
    file_size: Optional[int] = None
    last_modified: Optional[str] = None

class StencilShapeSummary(BaseModel):
    shape_id: int # Added shape_id for linking
    name: str
    width: Optional[float] = None
    height: Optional[float] = None

class StencilDetail(StencilSummary):
    shapes: List[StencilShapeSummary]
    last_scan: Optional[str] = None

class ShapeDetail(ShapeSummary): # Inherits from ShapeSummary
    width: Optional[float] = None
    height: Optional[float] = None
    geometry: Optional[Any] = None # Parsed JSON
    properties: Optional[Dict[str, Any]] = None # Parsed JSON

class ImportMetadata(BaseModel):
    source_url: Optional[str] = None
    capture_time: Optional[str] = None
    user_options: Optional[Dict] = {}

class ImportPayload(BaseModel):
    type: Literal['text', 'image'] = Field(..., description="The type of content being sent.")
    content: str = Field(..., description="The actual content (plain text or Base64 encoded image string).")
    metadata: Optional[ImportMetadata] = None

class ImportResponse(BaseModel):
    status: str
    message: Optional[str] = None

# --- Models for Favorites ---
class FavoriteItem(BaseModel):
    id: int
    item_type: Literal['stencil', 'shape']
    stencil_path: str
    shape_id: Optional[int] = None
    added_at: str
    stencil_name: Optional[str] = None # From JOIN in db.get_favorites
    shape_name: Optional[str] = None   # From JOIN in db.get_favorites

class AddFavoritePayload(BaseModel):
    stencil_path: str
    # Use shape_id for consistency, requires db.add_favorite_shape_by_id
    shape_id: Optional[int] = None

class SimpleStatusResponse(BaseModel): # Generic response for POST/DELETE success
    status: str
    message: Optional[str] = None

# --- Models for Collections ---
class CollectionShapeSummary(BaseModel): # To represent shapes within a collection detail
    shape_id: int
    shape_name: str
    stencil_path: str
    stencil_name: Optional[str] = None

class Collection(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str
    shape_count: Optional[int] = None # Populated in list view
    shapes: Optional[List[CollectionShapeSummary]] = None # Populated in detail view

class CreateCollectionPayload(BaseModel):
    name: str = Field(..., min_length=1)

class UpdateCollectionPayload(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    # Define how shapes are managed (replace all, or add/remove lists)
    # Option 1: Replace all shapes (simpler PUT)
    # shape_ids: Optional[List[int]] = None
    # Option 2: Add/Remove specific shapes
    add_shape_ids: Optional[List[int]] = None
    remove_shape_ids: Optional[List[int]] = None


# --- Models for Health & Status ---
class HealthStatus(BaseModel):
    api_status: str = "ok"
    db_status: str
    db_message: Optional[str] = None

class IntegrationStatus(BaseModel):
    visio_status: str
    message: Optional[str] = None
    error_message: Optional[str] = None



# --- Models for Commands ---
class CommandPayload(BaseModel):
    command: str = Field(..., description="The command to execute (e.g., 'trigger_scan').")
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the command.")

class CommandResponse(BaseModel):
    status: str
    message: Optional[str] = None
    result: Optional[Any] = None # For commands that return data



# --- Models for Commands ---
class CommandPayload(BaseModel):
    command: str = Field(..., description="The command to execute (e.g., 'trigger_scan').")
    params: Optional[Dict[str, Any]] = Field(None, description="Parameters for the command.")

class CommandResponse(BaseModel):
    status: str
    message: Optional[str] = None
    result: Optional[Any] = None # For commands that return data

# --- API Endpoints ---

@app.get("/", summary="Health Check")
async def read_root():
    """ Basic health check endpoint. """
    return {"message": "Visio Integration Bridge API is running"}

@app.get("/search", response_model=SearchResponse, summary="Search Shapes")
async def search_shapes_api(
    q: str,
    page: int = 1,
    size: int = 20,
    api_key: str = Depends(get_api_key)
):
    """ Searches for shapes using FTS5 or LIKE query. """
    if not q:
        raise HTTPException(status_code=400, detail="Search query 'q' is required.")
    if page < 1: page = 1
    if size < 1: size = 1
    if size > 100: size = 100 # Limit page size
    offset = (page - 1) * size
    try:
        search_results, total_count = db.search_shapes(
            search_term=q, limit=size, offset=offset, use_fts=True
        )
        # Map DB dictionary keys to Pydantic model fields if needed
        response_results = [ShapeSummary(**row) for row in search_results]
        return SearchResponse(
            results=response_results, total=total_count, page=page, size=len(response_results)
        )
    except Exception as e:
        print(f"Error during search: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during search: {e}")

# --- Stencil Endpoints ---

@app.get("/stencils", response_model=List[StencilSummary], summary="Get Stencil List")
async def get_stencils_api():
    """ Retrieves a summary list of all cached stencils. """
    try:
        stencils_data = db.get_cached_stencils()
        # Pydantic will validate the structure
        return [StencilSummary(**stencil) for stencil in stencils_data]
    except Exception as e:
        print(f"Error fetching stencils: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error fetching stencils: {e}")

@app.get("/stencils/{stencil_path:path}", response_model=StencilDetail, summary="Get Stencil Detail")
async def get_stencil_detail_api(stencil_path: str):
    """ Retrieves detailed information for a specific stencil by its path. """
    decoded_path = urllib.parse.unquote(stencil_path)
    try:
        stencil_data = db.get_stencil_by_path(decoded_path)
        if not stencil_data:
            raise HTTPException(status_code=404, detail=f"Stencil not found: {decoded_path}")
        # Convert shapes list to expected Pydantic model
        if 'shapes' in stencil_data and isinstance(stencil_data['shapes'], list):
             stencil_data['shapes'] = [StencilShapeSummary(**shape) for shape in stencil_data['shapes']]
        return StencilDetail(**stencil_data)
    except HTTPException as http_exc:
        raise http_exc # Re-raise 404
    except Exception as e:
        print(f"Error fetching stencil detail for {decoded_path}: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error fetching stencil detail: {e}")

# --- Shape Detail Endpoint ---
@app.get("/shapes/{shape_id}", response_model=ShapeDetail, summary="Get Shape Detail")
async def get_shape_detail_api(shape_id: int):
    """ Retrieves detailed information for a single shape by its ID. """
    try:
        shape_data = db.get_shape_by_id(shape_id)
        if not shape_data:
            raise HTTPException(status_code=404, detail=f"Shape not found with ID: {shape_id}")
        # Pydantic will handle validation
        return ShapeDetail(**shape_data)
    except HTTPException as http_exc:
        raise http_exc # Re-raise 404
    except Exception as e:
        print(f"Error fetching shape detail for ID {shape_id}: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error fetching shape detail: {e}")

# --- Favorites Endpoints ---

@app.get("/favorites", response_model=List[FavoriteItem], summary="Get Favorites")
async def get_favorites_api():
    """ Retrieves the list of favorited stencils and shapes. """
    try:
        favorites_data = db.get_favorites()
        # Pydantic validates the structure based on FavoriteItem model
        return [FavoriteItem(**fav) for fav in favorites_data]
    except Exception as e:
        print(f"Error fetching favorites: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error fetching favorites: {e}")

@app.post("/favorites", response_model=FavoriteItem, status_code=201, summary="Add Favorite")
async def add_favorite_api(payload: AddFavoritePayload):
    """ Adds a stencil or a specific shape to favorites. """
    try:
        new_fav_data = None
        if payload.shape_id is not None:
             print(f"Attempting to add favorite shape ID: {payload.shape_id} from stencil: {payload.stencil_path}")
             # Uses the method that takes shape_id directly
             new_fav_data = db.add_favorite_shape_by_id(payload.stencil_path, payload.shape_id)
        else:
             print(f"Attempting to add favorite stencil: {payload.stencil_path}")
             new_fav_data = db.add_favorite_stencil(payload.stencil_path)

        if not new_fav_data:
             # DB methods return None on conflict (already exists) or FK violation
             # Distinguish between 409 (duplicate) and 404/400 (bad stencil/shape ref)? - Requires more complex DB return/check
             raise HTTPException(status_code=409, detail="Item already favorited or associated stencil/shape not found.")

        # DB method returns dict matching FavoriteItem structure now
        return FavoriteItem(**new_fav_data)
    except HTTPException as http_exc: # Re-raise 409
         raise http_exc
    except Exception as e:
        print(f"Error adding favorite: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error adding favorite: {e}")

@app.delete("/favorites/{fav_id}", status_code=204, summary="Remove Favorite")
async def remove_favorite_api(fav_id: int):
    """ Removes an item from favorites by its favorite ID. """
    try:
        success = db.remove_favorite(fav_id) # DB method now returns bool
        if not success:
             raise HTTPException(status_code=404, detail=f"Favorite item with ID {fav_id} not found.")
        # Return No Content on success (FastAPI handles 204 automatically if no body)
        return
    except HTTPException as http_exc:
        raise http_exc # Re-raise 404
    except Exception as e:
        print(f"Error removing favorite ID {fav_id}: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error removing favorite: {e}")

# --- Collections Endpoints (STUBS) ---

@app.get("/collections", response_model=List[Collection], summary="Get Collections")
async def get_collections_api():
    """ Retrieves a list of all collections (names and basic info). """
    try:
        collections_raw = db.get_collections() # This method now includes shape_count
        return [Collection(**c) for c in collections_raw]
    except Exception as e:
        print(f"Error fetching collections: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error fetching collections: {e}")


@app.post("/collections", response_model=Collection, status_code=201, summary="Create Collection")
async def create_collection_api(payload: CreateCollectionPayload):
    """ Creates a new, empty collection. """
    try:
        new_collection = db.create_collection(payload.name)
        if not new_collection:
            raise HTTPException(status_code=409, detail=f"Collection name '{payload.name}' already exists.")
        # create_collection returns dict including shape_count=0
        return Collection(**new_collection)
    except sqlite3.IntegrityError: # Should be caught by db method, but belt-and-suspenders
         raise HTTPException(status_code=409, detail=f"Collection name '{payload.name}' already exists.")
    except Exception as e:
        print(f"Error creating collection: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error creating collection: {e}")

@app.get("/collections/{collection_id}", response_model=Collection, summary="Get Collection Details")
async def get_collection_details_api(collection_id: int):
    """ Retrieves details for a specific collection, including its shapes. """
    try:
       details = db.get_collection_details(collection_id)
       if not details:
           raise HTTPException(status_code=404, detail=f"Collection with ID {collection_id} not found.")
       # Map shapes data to CollectionShapeSummary
       if details.get('shapes'):
            details['shapes'] = [CollectionShapeSummary(**s) for s in details['shapes']]
       # Add shape_count (can be derived from shapes list length)
       details['shape_count'] = len(details.get('shapes', []))
       return Collection(**details)
    except HTTPException as http_exc:
        raise http_exc # Re-raise 404
    except Exception as e:
       print(f"Error fetching collection details for ID {collection_id}: {e}", file=sys.stderr)
       traceback.print_exc()
       raise HTTPException(status_code=500, detail=f"Internal server error fetching collection details: {e}")


@app.put("/collections/{collection_id}", response_model=Collection, summary="Update Collection")
async def update_collection_api(collection_id: int, payload: UpdateCollectionPayload):
    """ Updates a collection's name and/or adds/removes shapes. """
    try:
       updated_collection = db.update_collection(
           collection_id,
           name=payload.name,
           add_shape_ids=payload.add_shape_ids,
           remove_shape_ids=payload.remove_shape_ids
       )
       if not updated_collection:
           # Could be 404 (collection not found) or 409 (name conflict)
           raise HTTPException(status_code=404, detail=f"Collection with ID {collection_id} not found or update failed (e.g., name conflict).")
        # Map shapes data if returned by update_collection
       if updated_collection.get('shapes'):
            updated_collection['shapes'] = [CollectionShapeSummary(**s) for s in updated_collection['shapes']]
       updated_collection['shape_count'] = len(updated_collection.get('shapes', []))
       return Collection(**updated_collection)
    except HTTPException as http_exc:
         raise http_exc # Re-raise 404/409
    except Exception as e:
       print(f"Error updating collection {collection_id}: {e}", file=sys.stderr)
       traceback.print_exc()
       raise HTTPException(status_code=500, detail=f"Internal server error updating collection: {e}")


@app.delete("/collections/{collection_id}", status_code=204, summary="Delete Collection")

async def delete_collection_api(collection_id: int):
    """ Deletes a collection and its shape associations. """
    try:
       success = db.delete_collection(collection_id) # Assumes db method returns boolean
       if not success:
            raise HTTPException(status_code=404, detail=f"Collection with ID {collection_id} not found.")
       # Return 204 No Content implicitly on success
       return
    except HTTPException as http_exc:
         raise http_exc # Re-raise 404
    except Exception as e:
       print(f"Error deleting collection {collection_id}: {e}", file=sys.stderr)
       traceback.print_exc()
       raise HTTPException(status_code=500, detail=f"Internal server error deleting collection: {e}")



# --- Health and Status Endpoints ---

@app.get("/health", response_model=HealthStatus, summary="Health Check")
async def get_health_status():
    """ Checks the health of the API and its database connection. """
    db_ok = False
    db_msg = ""
    try:
        # Use a simple, fast query to check DB connection
        conn = db._get_conn() # Access internal method for direct check
        conn.execute("SELECT 1").fetchone()
        # Optionally run full integrity check, but might be slow
        # db_ok = db._check_integrity() # Assumes check_integrity returns bool
        db_ok = True # Assume OK if simple query works
        db_msg = "Database connection successful."
        print("Health Check: DB connection OK.")
    except Exception as e:
        db_ok = False
        db_msg = f"Database connection error: {e}"
        print(f"Health Check: DB connection FAILED - {e}", file=sys.stderr)

    return HealthStatus(
        api_status="ok",
        db_status="ok" if db_ok else "error",
        db_message=db_msg
    )

@app.get("/integration/status", response_model=IntegrationStatus, summary="Visio Integration Status")
async def get_integration_status():
    """ Checks the status of the connection to the Visio application. """
    try:
        status_dict = visio_integration.check_visio_connection()
        # Map the dict returned by the check function to the Pydantic model
        return IntegrationStatus(
            visio_status=status_dict.get("status", "error"),
            message=status_dict.get("message"),
            error_message=status_dict.get("error_message")
        )
    except Exception as e:
        print(f"Error checking Visio integration status: {e}", file=sys.stderr)
        traceback.print_exc()
        # Return an error status if the check function itself fails unexpectedly
        return IntegrationStatus(visio_status="error", error_message=f"Unexpected error during status check: {e}")



# --- Backend Action Endpoint ---

@app.post("/integration/command", response_model=CommandResponse, summary="Execute Backend Command")
async def execute_backend_command(payload: CommandPayload):
    """ Executes backend commands like triggering a stencil scan. """
    print(f"Received command: {payload.command} with params: {payload.params}")

    if payload.command == "trigger_scan":
        try:
            target_path = None
            if payload.params and 'path' in payload.params:
                target_path = payload.params['path']
                print(f"Scan requested for specified path: {target_path}")
            else:
                active_dir_data = db.get_active_directory()
                if active_dir_data and active_dir_data.get('path'):
                    target_path = active_dir_data['path']
                    print(f"Scan requested for active preset directory: {target_path}")
                else:
                    raise HTTPException(status_code=400, detail="Scan target path not specified and no active preset directory found.")

            if not target_path or not os.path.isdir(target_path):
                 raise HTTPException(status_code=400, detail=f"Invalid or non-existent directory specified for scan: {target_path}")

            # Run scan (assuming sync for now, consider background task for long scans)
            print(f"Starting scan for directory: {target_path}...")
            # Pass the globally initialized db instance
            scan_results = file_scanner.scan_directory(root_dir=target_path, db_instance=db)
            count = len(scan_results)
            print(f"Scan completed for {target_path}. Processed {count} new/updated files.")
            return CommandResponse(status="success", message=f"Scan initiated for '{target_path}'. Processed {count} new/updated files.", result={"processed_files": count})

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            print(f"Error during trigger_scan command: {e}", file=sys.stderr)
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Internal server error during scan: {e}")

    # --- Add other commands here ---
    # elif payload.command == "other_action":
    #    try: ...
    #    except Exception as e: ...

    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {payload.command}")


async def delete_collection_api(collection_id: int):
    """ Deletes a collection and its shape associations. """
    try:
       success = db.delete_collection(collection_id) # Assumes db method returns boolean
       if not success:
            raise HTTPException(status_code=404, detail=f"Collection with ID {collection_id} not found.")
       # Return 204 No Content implicitly on success
       return
    except HTTPException as http_exc:
         raise http_exc # Re-raise 404
    except Exception as e:
       print(f"Error deleting collection {collection_id}: {e}", file=sys.stderr)
       traceback.print_exc()
       raise HTTPException(status_code=500, detail=f"Internal server error deleting collection: {e}")


# --- Import Endpoint ---
@app.post("/import", response_model=ImportResponse, summary="Import Content to Visio")
async def import_content(payload: ImportPayload, api_key: str = Depends(get_api_key)):
    """ Receives content (text or image) from the Chrome extension and passes it to the Visio integration module. """
    print(f"Received import request: Type='{payload.type}', Metadata='{payload.metadata}'")
    try:
        if payload.type == "text":
            result = visio_integration.import_text_to_visio(payload.content, payload.metadata)
        elif payload.type == "image":
            if not payload.content.startswith('data:image'):
                 print(f"Warning: Received image content doesn't start with 'data:image...' - {payload.content[:60]}...")
            result = visio_integration.import_image_to_visio(payload.content, payload.metadata)
        else:
            raise HTTPException(status_code=400, detail="Invalid content type specified.")

        if result.get("status") == "success":
            return ImportResponse(status="success", message=result.get("message", "Import processed."))
        else:
            error_detail = result.get("message", "Integration failed")
            print(f"Error during Visio integration: {error_detail}")
            raise HTTPException(status_code=500, detail=f"Visio integration failed: {error_detail}")
    except visio_integration.VisioIntegrationError as vie:
         print(f"VisioIntegrationError in /import: {vie}", file=sys.stderr)
         raise HTTPException(status_code=503, detail=f"Visio integration error: {vie}")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error processing /import: {e}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    port = 5100
    print(f"Starting Visio Integration Bridge API on http://127.0.0.1:{port}")
    # PyInstaller PATH adjustment (if needed)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print("Running as a packaged executable.")
        _path = os.environ.get("PATH", "")
        _meipass = getattr(sys, '_MEIPASS')
        if _meipass not in _path:
            os.environ['PATH'] = _meipass + os.pathsep + _path
            print(f"Adjusted PATH for PyInstaller.")

    # Print the API key for initial setup
    print(f"\n\n===== API KEY =====\n{API_KEY}\n===================\n")
    print(f"IMPORTANT: Save this API key to use in your MCP server configuration on your Mac.")
    print(f"You can also set it as an environment variable VISIO_BRIDGE_API_KEY to keep it consistent.\n")

    # Listen on all interfaces (0.0.0.0) instead of just localhost
    uvicorn.run(app, host="0.0.0.0", port=port)