# Chrome Extension to Visio Integration Bridge — Detailed Technical Architecture

---

## 1. Overview  
This document provides an exhaustive technical blueprint for a Chrome extension tightly integrated with Microsoft Visio running on Windows. It outlines the extension’s feature workflows, local API specifications, data formats, security scope, and deep Windows automation via PyWin32 COM. It also details future-proof alternatives compatible with cross-platform workflows via Office.js and Graph APIs, to inform extensibility and portability considerations.

---

## 2. Chrome Extension Architecture

### 2.1 Core Features
- **Content Capture**: Web selection (via `content.js`), selected region screenshots (initiated via popup, using `region_selector.js` content script, `chrome.scripting.executeScript`, `chrome.tabs.captureVisibleTab`, and `OffscreenCanvas` in `background.js`).
- **User Workflow**: Context menu item (`background.js`) for text, Popup button (`popup.html`/`popup.js`) for screenshot region selection. Popup displays preview before sending via `background.js`.
- **Data Serialization**:  
  - Text snippets encoded as UTF-8 JSON  
  - Screenshots encoded as Base64 PNGs  

### 2.2 Permissions & Manifest
- **Permissions Required**:  
  - `contextMenus` (to add right-click options)  
  - `activeTab` (to access current page content)  
  - `scripting` (for injecting `region_selector.js`)
  - `storage` (optional, for retaining user settings like API port/token)
  - `host_permissions`: [`http://127.0.0.1:5100/*`, `http://localhost:5100/*`] (Default port 5100, explicitly allowing loopback IPs)
- **Manifest V3 Considerations**:  
  - Service worker (`background.js`) replaces background pages.
  - Use of `OffscreenCanvas` in service worker for image cropping.
  - CSP policies need to allow localhost POSTs but restrict remote origins  
- **UI Components**:  
  - Context menu item defined in `background.js`.
  - Popup dialog (`popup.html`, `popup.js`, vanilla JS) for initiating region selection, previewing content, and sending data.
  - Content scripts: `content.js` (for text selection response), `region_selector.js` (for drawing selection overlay).
  - Optional options page (not yet implemented) for configuration.

### 2.3 Data Flow & UX Triggers
- **Text**: User selects text -> Right-clicks -> Chooses "Send selected text to Visio" -> `background.js` gets text from `content.js` -> `background.js` constructs payload -> `background.js` sends POST to API.
- **Screenshot**: User opens popup -> Clicks "Capture Screenshot" -> `popup.js` requests `background.js` to inject `region_selector.js` -> User draws rectangle -> `region_selector.js` sends coords to `background.js` -> `background.js` captures tab, crops using `OffscreenCanvas`, sends cropped image dataURL to `popup.js` -> `popup.js` displays preview -> User clicks "Send Content to Visio" -> `popup.js` requests `background.js` to send data -> `background.js` constructs payload -> `background.js` sends POST to API.
- **API Call**: `background.js` uses `fetch` to POST JSON payload (`ImportPayload` model) to `http://127.0.0.1:5100/import`.
- Await API response, inform user of success/failure  
- Optional retry logic for server unavailability

---

## 3. Local API Server

### 3.1 Technology & Deployment
- Lightweight HTTP server: **FastAPI** (implemented in `main.py`).
- Runs on localhost only, listening on `127.0.0.1:5100` (default, defined in `main.py`). Configurable via code change initially.
- Packaged for Windows: `.pyw` background script, tray app, or bundled `.exe`  

### 3.2 API Endpoint Design

- **`POST /import`**  
  - **Payload**: JSON  
    ```json
    {
      "type": "text" | "image",
      "content": "<Base64 string or plain text>",
      "metadata": {
        "source_url": "...",
        "capture_time": "...",
        "user_options": {...}
      }
    }
    ```  
  - **Content-Type**: `application/json`  
  - **Response**: JSON result with status, shape ID(s), error details if any  

- **Security**:  
  - **Binding**: Only on localhost interface  
  - **Authentication**: Minimal or optional shared secret token in headers, configurable  
  - **No external exposure** or discovery mechanisms  
  - **CORS**: Accept only from extension or localhost  

### 3.3 Backend Processing Workflow
- Parse JSON, base64-decode image if needed  
- Dispatch to functions in `visio_integration.py` (e.g., `import_text_to_visio`, `import_image_to_visio`) via internal Python call from `main.py`.
- Return operation status synchronously  

---

## 4. Windows Visio Automation (Current Core)

### 4.1 PyWin32 COM Integration
- **Initialize** COM & connect to running Visio instance (or launch if absent)  
- **Target document**: active Visio diagram  
- **Text Insertion**:  
  - Create a new shape (`Drop` method or stencil shape)  
  - Set `.Text` property to captured text  
  - Optionally set formatting via `.Characters` object  
- **Image Insertion**:  
  - `Page.Import()` or embed image as new shape’s fill  
  - Support scaling, positioning presets  
- **Error Handling**:  
  - Detect COM errors (e.g., Visio app closed)  
  - Log exceptions with context  
  - Return status codes upstream

### 4.2 Deployment Constraints
- **Requires Windows** with installed Visio  
- **PyWin32 environment** (pythoncom, win32com.client)  
- Packaged dependencies managed with pyinstaller or virtualenv  
- **User must have running Visio instance, proper COM permissions**

---

## 5. Alternative & Future Integration Paths

### 5.1 Office.js Add-in Approach
- **Cross-platform** Chrome + Edge + Mac + Web  
- Deployable via Office Store or side-loaded  
- Accesses Visio **Web API surface**  
- Can **insert shapes, images, set shape data** via JS APIs  
- More limited than PyWin32 (cannot automate UI or complex shape logic)  
- **Requires Visio Online** or modern desktop app support  

### 5.2 Microsoft Graph API  
- REST over OAuth2, fully cross-platform  
- Access & manipulate **stored Visio files** in SharePoint/OneDrive  
- **Create/update Visio diagrams**, add shapes programmatically  
- Not real-time editing of local unsaved files  
- Needs Azure app registration, delegated/admin permissions  

### 5.3 Implications for Future-Proofing
- To extend beyond Windows, **migrate logic into Office.js add-in** where feasible  
- Use Chrome extension to **communicate with Office.js iframe**  
- For cloud-centric, add **Graph API adapter** to manipulate cloud files  
- Consider **hybrid**: local server for Windows-PyWin32, Office.js add-in for online/cross-platform  

---

## 6. Security, Privacy & Environment

- **Kept localhost-only** minimizes attack surface  
- Minimal optional shared secret token  
- Data never leaves user PC unless explicitly exported  
- No cloud storage unless future Graph API enabled  
- User controls enabling/disabling extension features  
- **No persistent sensitive data** stored in extension/local server  
- Token or port configuration stored in extension `storage.local` if needed, never synced  

---

## 7. Deployment & Developer Experience

- **Chrome Extension**:  
  - MV3 manifest, zipped for Chrome Store or side-loaded  
  - Update API URL via options page  
  - Sign with developer key  

- **API Server**:  
  - Packaged via PyInstaller (preferred), or run as `.pyw` script  
  - Optional tray icon to start/stop service  
  - Startup with Windows option  

- **Packaging Visio Integration**:  
  - Python virtualenv or standalone executable  
  - Ship with dependencies: pywin32, fastapi/flask, pyinstaller binary if bundled  

- **Debugging aids**:  
  - Console & file logging for API server and Visio integration  
  - Extension console logs errors during POST/interactions  

---

## 8. Summary

This architecture supports streamlined, low-friction transfer of rich web content directly into Visio diagrams via an isolated localhost integration bridge.  
It is optimized for immediate Windows/Visio/PyWin32 deployment, with deliberate design to enable gradual migration toward cross-platform, cloud, and Office.js based workflows as Microsoft’s Office ecosystem evolves.