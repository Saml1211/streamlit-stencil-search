# Progress: Chrome Extension to Visio Bridge (Updated: 2025-07-07)

## Completed Features

### Chrome Extension (`chrome-extension/`)
- ✅ **Core Structure**: Manifest V3 (`manifest.json`), Service Worker (`background.js`), Popup (`popup.html`, `popup.js`), Content Script (`content.js`), Region Selector (`region_selector.js`), Icons (`icons/`).
- ✅ **Text Capture**: Context menu trigger, selection retrieval via `content.js`, message passing to `background.js`.
- ✅ **Screenshot Capture (Region)**: Popup button trigger, injection of `region_selector.js`, coordinate capture, `captureVisibleTab` call, cropping via `OffscreenCanvas` in `background.js`, result sent back to popup.
- ✅ **API Communication**: `fetch` POST requests implemented in `background.js` to send captured data (text/image) to `http://127.0.0.1:5100/import`. Basic error handling for network/HTTP errors.

### Local API Server (`local-api-server/`)
- ✅ **Core Structure**: Basic FastAPI project (`main.py`), dependencies (`requirements.txt`).
- ✅ **API Endpoint**: `/import` POST endpoint implemented, accepts JSON payload (`ImportPayload` model), validates input type.
- ✅ **Visio Integration Stub**: `visio_integration.py` created with `get_visio_app()` using `win32com.client` and basic COM error handling. Placeholder functions `import_text_to_visio` and `import_image_to_visio`.
- ✅ **API -> Visio Stub Integration**: `/import` endpoint in `main.py` now calls the placeholder functions in `visio_integration.py`.

## In Progress

- 🔄 Refining error handling and user feedback in the Chrome extension (e.g., notifications for API errors).
- 🔄 Improving state management in `popup.js` (especially if closed/reopened during async ops).

## What's Left to Build

### High Priority
1.  📋 **Implement Visio Text Insertion**: Replace placeholder in `visio_integration.py` with actual PyWin32 COM code to create a shape and insert text from `payload.content`.
2.  📋 **Implement Visio Image Insertion**: Replace placeholder in `visio_integration.py`. Requires handling Base64 decoding, saving image temporarily, and using `Page.Import()` or shape fill with the image file path.
3.  📋 **API Server Packaging**: Package the local API server as a standalone Windows executable (e.g., using PyInstaller), ensuring PyWin32 dependencies and DLLs are correctly bundled.
4.  📋 **Extension Configuration**: Implement an options page or mechanism to configure the API server port (currently hardcoded as 5100).
5.  📋 **Robust Error Handling**: Add comprehensive error handling in `visio_integration.py` for various Visio COM scenarios (document closed, page unavailable, invalid operations).

### Medium Priority
1.  📋 **User Options**: Allow users to select image insertion method (e.g., embed vs. background) in the popup UI and pass this via metadata.
2.  📋 **API Authentication**: Implement the optional token handshake between extension and API if required.
3.  📋 **Installer**: Create an installer for the local API server for easier deployment.

### Low Priority / Future Features
1.  📋 Investigate/Implement Office.js or Graph API alternatives for cross-platform support.
2.  📋 Add more sophisticated preview/editing options in the popup.

## Known Issues
- `visio_integration.py` currently only contains placeholder logic; no actual Visio automation occurs yet.
- Popup state (`capturedData`) is not persistent if the popup is closed and reopened during an operation (using temporary `sessionStorage` as a partial workaround).
- CORS origins in `main.py` might need refinement for the packaged extension ID.
- PyInstaller packaging for PyWin32 requires careful configuration to include necessary DLLs (`pywintypes`).