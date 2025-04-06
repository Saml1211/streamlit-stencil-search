# Chrome Extension + Local Visio Integration Bridge - Architecture

---

### **Chrome Extension Features**

- **Capture selected text**: User highlights webpage text, triggers context menu or popup button to "Send to Visio"
- **Capture screenshot**: User clicks to enter crop mode, selects area, screenshot is captured & optionally previewed
- **Popup UI**: Confirm content before sending, select embed options
- **Send captured data** via HTTP POST to `http://localhost:<port>/import` API on the user's PC

---

### **Local HTTP API Server**

- Runs on **Windows PC** alongside Visio
- Built with **FastAPI** or **Flask**
- Exposes **`/import`** endpoint accepting:
  - **Base64 image screenshots**
  - **Plain text snippets**
- Backend calls the existing **`visio_integration.py`** using **PyWin32 COM**
  - Insert text as a **new shape with label**
  - Insert image as an **embedded picture** or **shape background**

---

### **Workflow**

1. User **selects webpage content or screenshot**
2. Chrome extension **captures content**
3. Extension **POSTs** data to local API server
4. API server **embeds content** into an open Visio file

---

### **Security**

- API is **localhost-only**
- Optional API **token handshake** for auth

---

### **Integration Details**

- **Text content** → create Visio shape with text label
- **Screenshots** → embed image as shape or background

---

### **Development Stages**

1. **Chrome Extension**
   - Manifest, content script, popup
   - Capture selection/screenshot
   - POST to API
2. **Local API Server**
   - FastAPI endpoints
   - Call `visio_integration.py` to embed into Visio
3. **Integration**
   - Automate content flow from Chrome into Visio diagrams

---

# End of plan