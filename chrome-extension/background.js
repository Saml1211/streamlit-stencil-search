// Service Worker for Visio Content Importer Extension
// Handles context menu creation, message passing, script injection, cropping, and API communication.

console.log("Visio Importer Service Worker started.");

const CONTEXT_MENU_ID = "SEND_TEXT_TO_VISIO";
const API_URL = "http://127.0.0.1:5100/import"; // Ensure port matches main.py and host_permissions

// --- Context Menu Setup ---
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: "Send selected text to Visio",
    contexts: ["selection"]
  });
  console.log("Context menu created.");
});

// --- Context Menu Click Handler ---
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === CONTEXT_MENU_ID && tab && tab.id) {
    console.log("Context menu clicked. Requesting selected text from tab:", tab.id);
    chrome.tabs.sendMessage(tab.id, { action: "getSelectedText" }, (response) => {
      if (chrome.runtime.lastError) {
        console.error("Error sending message to content script:", chrome.runtime.lastError.message);
      } else if (response && response.selectedText) {
        const capturedText = response.selectedText;
        console.log("Received selected text:", capturedText);
        const payload = {
          type: "text",
          content: capturedText,
          metadata: {
            source_url: tab.url,
            capture_time: new Date().toISOString()
          }
        };
        sendDataToApi(payload); // Send text data to API
      } else {
        console.log("No response or empty text received from content script.");
      }
    });
  }
});

// --- API Communication ---
async function sendDataToApi(payload) {
  console.log("Attempting to send data to API:", payload.type);
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let responseData = {};
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
        responseData = await response.json();
    } else {
        responseData.message = await response.text(); // Get text if not JSON
    }

    if (!response.ok) {
      const errorDetail = responseData.detail || responseData.message || `HTTP error! status: ${response.status}`;
      console.error("API request failed:", errorDetail);
      // TODO: Notify user (e.g., chrome.notifications API)
      return { success: false, message: errorDetail };
    }

    console.log("API response received:", responseData);
    // TODO: Notify user of success
    return { success: true, data: responseData };

  } catch (error) {
    console.error("Error sending data to API:", error);
    // TODO: Notify user (e.g., "API server not running?")
    return { success: false, message: `Network error or API unreachable: ${error.message}` };
  }
}

// --- Cropping Function ---
async function cropImage(imageDataUrl, coords) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = async () => {
            const scale = coords.devicePixelRatio || 1;
            const cropWidth = Math.round(coords.width * scale);
            const cropHeight = Math.round(coords.height * scale);
            const cropX = Math.round(coords.x * scale);
            const cropY = Math.round(coords.y * scale);

            if (cropWidth <= 0 || cropHeight <= 0) {
                return reject(new Error("Invalid crop dimensions calculated."));
            }
             // Basic bounds check
             if (cropX < 0 || cropY < 0 || cropX + cropWidth > img.width || cropY + cropHeight > img.height) {
                console.warn(`Crop area [${cropX},${cropY},${cropWidth},${cropHeight}] might exceed image bounds [${img.width},${img.height}]. Attempting anyway.`);
                // Consider clamping here if needed, though drawImage might handle it.
             }

            try {
                const canvas = new OffscreenCanvas(cropWidth, cropHeight);
                const ctx = canvas.getContext('2d');
                if (!ctx) {
                   return reject(new Error("Failed to get OffscreenCanvas 2D context."));
                }

                ctx.drawImage(img, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight);

                // Convert canvas to Blob, then to data URL
                const blob = await canvas.convertToBlob({ type: 'image/png' });
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = (err) => reject(new Error(`FileReader error: ${err}`));
                reader.readAsDataURL(blob);

            } catch (error) {
                console.error("Error during canvas drawImage or blob conversion:", error);
                reject(new Error(`Canvas processing failed: ${error.message}`));
            }
        };
        img.onerror = (err) => {
            reject(new Error(`Failed to load image for cropping: ${err}`));
        };
        img.src = imageDataUrl;
    });
}


// --- Message Listener ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Background received message:", request);

  if (request.action === "injectRegionSelector" && request.tabId) {
    console.log(`Injecting region_selector.js into tab ${request.tabId}`);
    chrome.scripting.executeScript({
      target: { tabId: request.tabId },
      files: ['region_selector.js']
    }).then(() => {
      console.log("Region selector script injected successfully.");
      sendResponse({ status: "injection_started" });
    }).catch(err => {
      console.error("Failed to inject region selector script:", err);
      sendResponse({ status: "injection_failed", message: err.message });
    });
    return true; // Indicate async response

  } else if (request.action === "regionSelected") {
    // Received coordinates from region_selector.js
    console.log("Received selected region coordinates:", request.coords);
    const tabId = sender.tab?.id;
    const coords = request.coords;

    if (!tabId) {
         console.error("Cannot capture region, sender tab ID is missing.");
         sendResponse({status: "error", message: "Sender tab ID missing."});
         return true; // Acknowledge error
    }

    console.log("Initiating capture for selected region...");
    chrome.tabs.captureVisibleTab(tabId, { format: "png" }, (imageDataUrl) => {
       if (chrome.runtime.lastError) {
           console.error("Error capturing tab for region:", chrome.runtime.lastError.message);
           // Attempt to notify content script (best effort)
           if(tabId) chrome.tabs.sendMessage(tabId, {action: "regionCaptureFailed", error: chrome.runtime.lastError.message}).catch(e => console.log("Couldn't notify content script of capture fail:", e));
           sendResponse({status: "error", message: "Capture failed"});
       } else {
           console.log("Full tab captured, proceeding to crop...");
           cropImage(imageDataUrl, coords)
               .then(croppedImageDataUrl => {
                   console.log("Cropping successful, sending cropped image to popup.");
                   // Send message to potentially update popup (if open)
                   chrome.runtime.sendMessage({
                       action: "displayCapturedRegion",
                       imageDataUrl: croppedImageDataUrl
                       // We could store this in storage API for popup to retrieve later if needed
                   });
                   sendResponse({status: "capture_and_crop_complete", imageDataUrl: croppedImageDataUrl }); // Send data back to content script requester
               })
               .catch(error => {
                   console.error("Cropping failed:", error);
                   sendResponse({status: "error", message: `Cropping failed: ${error.message}`});
               });
       }
    });
    return true; // Indicate async response

  } else if (request.action === "sendToApi" && request.data) {
     // Handle request from popup to send data
     sendDataToApi(request.data).then(response => {
         sendResponse(response); // Send API result back to popup
     }).catch(error => {
         sendResponse({ success: false, message: error.message });
     });
     return true; // Indicate async response
   }

  // If message not handled, return false or simply don't return anything.
  // Returning true incorrectly keeps the message channel open unnecessarily.
});