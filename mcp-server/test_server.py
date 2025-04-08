#!/usr/bin/env python3
"""
Test script for the Visio Bridge MCP Server

This script tests the basic functionality of the MCP server by simulating
tool calls and checking the responses.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add the current directory to the path so we can import the server module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the server module
from visio_bridge_server import (
    import_text_to_visio,
    import_image_to_visio,
    search_shapes,
    get_shape_details,
    get_stencil_list,
    check_visio_connection
)

async def run_tests():
    """Run a series of tests against the MCP server tools."""
    print("Testing Visio Bridge MCP Server tools...")

    # Test 1: Check Visio Connection
    print("\n=== Test 1: Check Visio Connection ===")
    try:
        result = await check_visio_connection()
        print(f"Result: {result}")

        # If we can't connect to the local API, don't run the other tests
        if "Error" in result:
            print("\nCannot connect to local API server. Skipping remaining tests.")
            print("Please make sure the local API server is running on port 5100.")
            return
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nCannot connect to local API server. Skipping remaining tests.")
        print("Please make sure the local API server is running on port 5100.")
        return

    # Test 2: Search Shapes
    print("\n=== Test 2: Search Shapes ===")
    try:
        result = await search_shapes("network")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")

    # Test 3: Get Stencil List
    print("\n=== Test 3: Get Stencil List ===")
    try:
        result = await get_stencil_list()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")

    # Test 4: Import Text
    print("\n=== Test 4: Import Text ===")
    try:
        result = await import_text_to_visio("Test text from MCP server", {"source": "MCP test"})
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")

    # Test 5: Import Image (using a simple base64 encoded 1x1 pixel)
    print("\n=== Test 5: Import Image ===")
    try:
        # Simple 1x1 transparent PNG
        base64_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        result = await import_image_to_visio(base64_image, {"source": "MCP test"})
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")

    print("\nAll tests completed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
