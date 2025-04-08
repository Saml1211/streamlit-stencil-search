# Active Context: Visio Bridge Integration Suite (Updated: 2025-07-10)

## Current Work Focus

The project has expanded to include an MCP (Model Context Protocol) server implementation that enables AI assistants like Claude to interact with Visio through the existing local API. This new component bridges the gap between AI assistants and Visio, allowing for natural language interaction with the stencil database and Visio operations.

The implementation of the MCP server is now complete, with all necessary tools implemented for AI assistants to interact with Visio, including text import, image import, shape search, and more.

The previous focus on implementing core Visio automation logic within `local-api-server/visio_integration.py` remains important, but is now complemented by the completed MCP server integration.

## Recent Changes

### MCP Server Implementation (July 2025)

- Created `mcp-server` directory with MCP server implementation (`visio_bridge_server.py`)
- Implemented bridge layer to communicate with the local API server
- Added tools for text import, image import, shape search, and more
- Created comprehensive documentation in the `docs` directory
  - Added MCP-Server-Documentation.md with full server details
  - Added MCP-Server-QuickStart.md guide
  - Added MCP-Server-Architecture.md technical breakdown
  - Added Remote-Visio-Setup.md for Mac users
- Updated project README to include MCP server information
- Added configuration files for the MCP server
- Created startup scripts for both Windows (.bat) and Unix (.sh)
- Implemented test script for verifying server functionality
- Set up remote connection support via configuration (setup_remote.sh)

### Chrome Extension & Local API (Request req-8 Summary)

- Created `chrome-extension` directory with Manifest V3, service worker, popup, content scripts
- Implemented context menu for text capture
- Implemented region selection screenshot mechanism
- Established `fetch` communication from the extension's service worker to the local API
- Created `local-api-server` directory with FastAPI (`main.py`)
- Implemented `/import` API endpoint with Pydantic validation
- Created `visio_integration.py` stub with basic COM connection function

## Active Decisions

### MCP Server

- **Protocol**: Model Context Protocol (MCP) selected for AI assistant integration
- **Implementation**: Python MCP SDK used for server implementation
- **Bridge Pattern**: Bridge layer implemented to communicate with local API
- **Tool Design**: Tools designed to match existing API endpoints
- **Error Handling**: Comprehensive error handling with detailed logging
- **Configuration**: JSON-based configuration for server settings
- **Security**: Rate limiting implemented to prevent abuse
- **Remote Support**: Optional configuration for connecting to remote Windows machines

### Chrome Extension & Local API

- **Screenshot Method**: Region selection implemented instead of simple capture + crop
- **Cropping Location**: Performed in the service worker using `OffscreenCanvas`
- **API Framework**: FastAPI selected for the local server
- **Visio Integration**: Initial focus on PyWin32 COM (Windows only)
- **Error Handling**: Basic error handling added for COM connection, API calls, and script injection
- **State Management**: Basic state handled via messages; `sessionStorage` used in popup

## Current Tasks

- MCP Server implementation for Visio Bridge is complete
- Documentation for MCP Server has been created
- README has been updated to include MCP Server information

## Next Steps (High-Level)

1. **Test MCP Server with Claude**: Test the MCP server with Claude for Desktop to verify functionality.
2. **Implement Visio Text Insertion**: Complete the implementation of `visio_integration.import_text_to_visio`.
3. **Implement Visio Image Insertion**: Complete the implementation of `visio_integration.import_image_to_visio`.
4. **Enhance MCP Server**: Add more tools and capabilities to the MCP server based on user feedback.
5. **Packaging**: Create executable packages for both the local API server and MCP server.
6. **Testing**: Conduct end-to-end testing on Windows machines with Visio installed.

## Technical Considerations

- Handling different Visio versions/states via COM
- Managing temporary files for image insertion securely and reliably
- Ensuring correct thread handling for COM objects if FastAPI runs workers
- Packaging the Python server with PyInstaller, including PyWin32 DLLs
- Configuring Claude for Desktop to work with the MCP server
- Securing the MCP server with appropriate authentication and authorization
- Optimizing performance for large stencil databases
- Handling error cases gracefully in both the local API and MCP server
- Testing cross-platform behavior with remote Visio server connections
