#!/usr/bin/env python3
"""
Visio Bridge MCP Server

This server exposes Visio integration capabilities through the Model Context Protocol,
allowing other MCP-compatible tools to interact with the local Visio bridge.
"""

import os
import sys
import json
import logging
import asyncio
import traceback
from typing import Any, Dict, List, Optional, Union
import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("visio_bridge_mcp.log")
    ]
)
logger = logging.getLogger("visio_bridge_mcp")

# Initialize FastMCP server
mcp = FastMCP("visio-bridge")

# Constants
# Replace WINDOWS_IP with the actual IP address of your Windows machine
LOCAL_API_BASE = os.environ.get("VISIO_BRIDGE_API_URL", "http://WINDOWS_IP:5100")
# Replace API_KEY with the API key displayed when starting the server on Windows
API_KEY = os.environ.get("VISIO_BRIDGE_API_KEY", "YOUR_API_KEY_HERE")
DEFAULT_TIMEOUT = 30.0  # seconds

# ---- Bridge Layer ----

async def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """Make a request to the local Visio Bridge API with proper error handling."""
    url = f"{LOCAL_API_BASE}/{endpoint.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": API_KEY
    }

    logger.info(f"Making {method} request to {url}")
    if data:
        logger.debug(f"Request data: {json.dumps(data)[:200]}...")

    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                response = await client.post(url, json=data, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            # Try to parse error response if it's JSON
            try:
                error_data = e.response.json()
                error_message = error_data.get("detail", str(e))
            except Exception:
                error_message = f"HTTP error {e.response.status_code}: {e.response.text}"
            raise RuntimeError(error_message)
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise RuntimeError(f"Failed to connect to local Visio Bridge API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Unexpected error: {str(e)}")

# ---- Tool Implementations ----

@mcp.tool()
async def import_text_to_visio(text_content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Import text content into Visio.

    This tool sends text to the local Visio instance, which will create a new shape
    with the text content.

    Args:
        text_content: The text to import into Visio
        metadata: Optional metadata about the text (source, formatting, etc.)

    Returns:
        A confirmation message with details about the imported content
    """
    if not text_content:
        return "Error: No text content provided."

    # Prepare the payload for the local API
    payload = {
        "type": "text",
        "content": text_content,
        "metadata": metadata or {}
    }

    try:
        result = await make_api_request("import", method="POST", data=payload)

        if result.get("status") == "success":
            return f"Successfully imported text to Visio. Shape ID: {result.get('shape_id', 'unknown')}"
        else:
            return f"Failed to import text: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error importing text: {str(e)}", exc_info=True)
        return f"Error importing text to Visio: {str(e)}"

@mcp.tool()
async def import_image_to_visio(image_data: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Import an image into Visio.

    This tool sends a base64-encoded image to the local Visio instance, which will
    create a new shape with the image.

    Args:
        image_data: Base64-encoded image data (can include data URI prefix)
        metadata: Optional metadata about the image (source, dimensions, etc.)

    Returns:
        A confirmation message with details about the imported content
    """
    if not image_data:
        return "Error: No image data provided."

    # Ensure image_data has proper data URI format if not already
    if not image_data.startswith("data:image"):
        # Try to determine image type or default to png
        if image_data.startswith("/9j/"):
            mime_type = "image/jpeg"
        else:
            mime_type = "image/png"
        image_data = f"data:{mime_type};base64,{image_data}"

    # Prepare the payload for the local API
    payload = {
        "type": "image",
        "content": image_data,
        "metadata": metadata or {}
    }

    try:
        result = await make_api_request("import", method="POST", data=payload)

        if result.get("status") == "success":
            return f"Successfully imported image to Visio. Shape ID: {result.get('shape_id', 'unknown')}"
        else:
            return f"Failed to import image: {result.get('message', 'Unknown error')}"
    except Exception as e:
        logger.error(f"Error importing image: {str(e)}", exc_info=True)
        return f"Error importing image to Visio: {str(e)}"

@mcp.tool()
async def search_shapes(query: str, page: int = 1, size: int = 20) -> str:
    """Search for shapes in the stencil database.

    This tool searches the local stencil database for shapes matching the query.

    Args:
        query: The search term to look for in shape names and metadata
        page: Page number for pagination (starting at 1)
        size: Number of results per page (max 100)

    Returns:
        A formatted list of matching shapes with their details
    """
    if not query:
        return "Error: No search query provided."

    try:
        # Validate and adjust pagination parameters
        if page < 1:
            page = 1
        if size < 1:
            size = 1
        if size > 100:
            size = 100

        # Make the search request
        result = await make_api_request(f"search?q={query}&page={page}&size={size}")

        # Format the results
        if not result.get("results"):
            return f"No shapes found matching '{query}'."

        total = result.get("total", 0)
        current_page = result.get("page", 1)
        results_count = len(result.get("results", []))

        # Build the response
        response = [f"Found {total} shapes matching '{query}' (showing page {current_page}, {results_count} results):"]

        for idx, shape in enumerate(result.get("results", []), 1):
            response.append(f"{idx}. {shape.get('shape_name', 'Unnamed')} - " +
                          f"Stencil: {shape.get('stencil_name', 'Unknown')}")

        # Add pagination info if needed
        if total > page * size:
            next_page = page + 1
            response.append(f"\nUse 'search_shapes(query=\"{query}\", page={next_page}, size={size})' to see more results.")

        return "\n".join(response)
    except Exception as e:
        logger.error(f"Error searching shapes: {str(e)}", exc_info=True)
        return f"Error searching shapes: {str(e)}"

@mcp.tool()
async def get_shape_details(shape_id: int) -> str:
    """Get detailed information about a specific shape.

    This tool retrieves detailed information about a shape by its ID.

    Args:
        shape_id: The unique identifier of the shape

    Returns:
        Detailed information about the shape
    """
    if not shape_id:
        return "Error: No shape ID provided."

    try:
        result = await make_api_request(f"shapes/{shape_id}")

        if not result:
            return f"No shape found with ID {shape_id}."

        # Format the shape details
        details = [f"Shape Details for ID {shape_id}:"]
        details.append(f"Name: {result.get('shape_name', 'Unnamed')}")
        details.append(f"Stencil: {result.get('stencil_name', 'Unknown')}")
        details.append(f"Stencil Path: {result.get('stencil_path', 'Unknown')}")

        # Add any additional metadata if available
        if "metadata" in result:
            details.append("\nMetadata:")
            for key, value in result.get("metadata", {}).items():
                details.append(f"  {key}: {value}")

        return "\n".join(details)
    except Exception as e:
        logger.error(f"Error getting shape details: {str(e)}", exc_info=True)
        return f"Error getting shape details: {str(e)}"

@mcp.tool()
async def get_stencil_list() -> str:
    """Get a list of all available stencils.

    This tool retrieves a list of all stencils in the database.

    Returns:
        A formatted list of stencils with their details
    """
    try:
        result = await make_api_request("stencils")

        if not result:
            return "No stencils found in the database."

        # Format the results
        response = [f"Found {len(result)} stencils:"]

        for idx, stencil in enumerate(result, 1):
            response.append(f"{idx}. {stencil.get('name', 'Unnamed')} - " +
                          f"Shapes: {stencil.get('shape_count', 0)}, " +
                          f"Path: {stencil.get('path', 'Unknown')}")

        return "\n".join(response)
    except Exception as e:
        logger.error(f"Error getting stencil list: {str(e)}", exc_info=True)
        return f"Error getting stencil list: {str(e)}"

@mcp.tool()
async def check_visio_connection() -> str:
    """Check if the local Visio instance is connected and ready.

    This tool checks the connection status of the local Visio instance.

    Returns:
        A status message indicating whether Visio is connected
    """
    try:
        result = await make_api_request("")  # Root endpoint for health check

        if result.get("message", "").lower().find("running") >= 0:
            return "Visio Bridge API is running and ready to accept commands."
        else:
            return f"Visio Bridge API responded but with unexpected message: {result.get('message', 'No message')}"
    except Exception as e:
        logger.error(f"Error checking Visio connection: {str(e)}", exc_info=True)
        return f"Error: Could not connect to Visio Bridge API. Make sure the local API server is running: {str(e)}"

# ---- Main Execution ----

if __name__ == "__main__":
    logger.info("Starting Visio Bridge MCP Server")

    # Check if the local API is available before starting
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(check_visio_connection())
        logger.info("Successfully connected to local Visio Bridge API")
    except Exception as e:
        logger.warning(f"Could not connect to local Visio Bridge API: {str(e)}")
        logger.warning("The MCP server will start, but tools may not work until the local API is available")

    # Run the MCP server
    mcp.run(transport='stdio')
