# Active Context: Chrome Extension to Visio Bridge (Updated: 2025-07-07)

## Current Work Focus
The initial implementation phase (MCP Task Request `req-8`) for the Chrome Extension and Local API Server is complete. This phase established the foundational project structures, core communication pathways, and placeholder logic for key features like text capture, region selection screenshotting, API interaction, and basic COM connection.

The current focus shifts to **implementing the core Visio automation logic** within the `local-api-server/visio_integration.py` module. This involves replacing the placeholder functions with actual PyWin32 COM calls to insert captured text and images into the active Visio document.

## Recent Changes (Request req-8 Summary)
- Created `chrome-extension` directory with Manifest V3, service worker, popup, content scripts (`content.js`, `region_selector.js`), and icons.
- Implemented context menu for text capture.
- Implemented region selection screenshot mechanism (trigger, script injection, coordinate capture, cropping via OffscreenCanvas).
- Established `fetch` communication from the extension's service worker to the local API.
- Created `local-api-server` directory with FastAPI (`main.py`) and initial dependencies (`requirements.txt`).
- Implemented `/import` API endpoint with Pydantic validation.
- Created `visio_integration.py` stub with basic COM connection function (`get_visio_app`) and placeholder import functions.
- Integrated calls from `main.py` to `visio_integration.py`.

## Active Decisions
- **Screenshot Method**: Region selection implemented instead of simple capture + crop.
- **Cropping Location**: Performed in the service worker using `OffscreenCanvas`.
- **API Framework**: FastAPI selected for the local server.
- **Visio Integration**: Initial focus on PyWin32 COM (Windows only).
- **Error Handling**: Basic error handling added for COM connection, API calls, and script injection. More detailed Visio COM error handling is pending.
- **State Management**: Basic state handled via messages; `sessionStorage` used in popup as temporary measure (needs refinement).

## Current Tasks
- No active MCP tasks. Request `req-8` is complete. Awaiting planning for the next phase.

## Next Steps (High-Level)
1.  **Plan next implementation phase**: Define new tasks in MCP Task Manager for implementing Visio text/image insertion via PyWin32.
2.  **Implement Visio Text Insertion**: Flesh out `visio_integration.import_text_to_visio`.
3.  **Implement Visio Image Insertion**: Flesh out `visio_integration.import_image_to_visio` (including Base64 decoding and temp file handling).
4.  **Refine Error Handling**: Improve Visio COM error details and user feedback in the extension.
5.  **Testing**: Test the end-to-end flow on a Windows machine with Visio installed.

## Technical Considerations
- Handling different Visio versions/states via COM.
- Managing temporary files for image insertion securely and reliably.
- Ensuring correct thread handling for COM objects if FastAPI runs workers.
- Packaging the Python server with PyInstaller, including PyWin32 DLLs.
- Refining popup state management for robustness.