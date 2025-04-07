// Script for popup.html logic

console.log("Popup script loaded.");

// Global-like variable to hold captured data (text or image data URL)
// Note: State management will need improvement if popup closes during async operations.
let capturedData = null;

document.addEventListener('DOMContentLoaded', () => {
    const captureButton = document.getElementById('capture-screenshot-button');
    const sendButton = document.getElementById('send-button');
    const statusDiv = document.getElementById('status');
    const previewDiv = document.getElementById('content-preview');

    previewDiv.innerHTML = 'No content captured yet.'; // Initial state
    statusDiv.textContent = 'Ready.'; // Initial status

    // --- Event Listener for Capture Button ---
    captureButton.addEventListener('click', () => {
        statusDiv.textContent = 'Initiating region selection...';
        previewDiv.innerHTML = ''; // Clear previous preview
        capturedData = null;

        // Get the current active tab to inject the script into
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (chrome.runtime.lastError || !tabs || tabs.length === 0 || !tabs[0].id) {
                statusDiv.textContent = 'Error: Could not find active tab.';
                console.error("Error querying active tab:", chrome.runtime.lastError || "No active tab found");
                return;
            }
            const targetTabId = tabs[0].id;

            // Send message to background script to inject the region selector
            console.log(`Sending injectRegionSelector message for tab ${targetTabId}`);
            chrome.runtime.sendMessage({ action: "injectRegionSelector", tabId: targetTabId }, (response) => {
                if (chrome.runtime.lastError) {
                    statusDiv.textContent = `Error injecting script: ${chrome.runtime.lastError.message}`;
                    console.error("Error receiving response from injectRegionSelector:", chrome.runtime.lastError);
                } else if (response && response.status === "injection_started") {
                    statusDiv.textContent = 'Select a region on the page...';
                    // Close popup after initiating selection; background handles the rest
                    window.close();
                } else {
                     statusDiv.textContent = `Failed to start region selection: ${response?.message || 'Unknown reason'}.`;
                     console.error("Failed response from injectRegionSelector:", response);
                }
            });
        });
    });

    // --- Event Listener for Send Button ---
    sendButton.addEventListener('click', () => {
        // Note: `capturedData` might be stale if the popup was closed and reopened.
        // This needs refinement using chrome.storage.local later.
        if (!capturedData) {
             statusDiv.textContent = 'Nothing captured to send.';
             return;
        }
        statusDiv.textContent = 'Sending...';

        // Get metadata (optional, could be expanded)
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            let metadata = { capture_time: new Date().toISOString() };
             if (tabs.length > 0) {
                 metadata.source_url = tabs[0].url;
             }

            const payload = {
                 type: capturedData.type, // 'text' or 'image'
                 content: capturedData.content,
                 metadata: metadata
            };

            console.log("Sending data to background script for API call:", payload);
            chrome.runtime.sendMessage({ action: "sendToApi", data: payload }, (response) => {
               if (chrome.runtime.lastError) {
                   statusDiv.textContent = `Error sending: ${chrome.runtime.lastError.message}`;
                   console.error("Error receiving response from sendToApi:", chrome.runtime.lastError);
               } else if (response && response.success) {
                   statusDiv.textContent = 'Sent successfully!';
                   // Optionally close popup after success
                   setTimeout(() => window.close(), 1500);
               } else {
                   statusDiv.textContent = `Send failed: ${response ? response.message : 'Unknown error'}`;
                   console.error("Failed response from sendToApi:", response);
               }
            });
        });
    });

}); // End of DOMContentLoaded

// --- Message Listener (Top Level) ---
// Handles messages from the background script, e.g., displaying the final image
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // This listener might run *after* the popup was initially closed.
    // If the user reopens the popup, this helps display the result.
    if (request.action === "displayCapturedRegion" && request.imageDataUrl) {
        console.log("Received displayCapturedRegion message.");

        // Store data for potential later use by the send button
        // Using session storage which persists only while the extension is running
        // Use chrome.storage.local for persistence across browser sessions if needed
        sessionStorage.setItem('lastCapturedData', JSON.stringify({
            type: 'image',
            content: request.imageDataUrl
        }));

        // Try to update the UI if the popup happens to be open when message arrives
        const previewDiv = document.getElementById('content-preview');
        const statusDiv = document.getElementById('status');
        if (previewDiv && statusDiv) {
             const img = document.createElement('img');
             img.src = request.imageDataUrl;
             previewDiv.innerHTML = '';
             previewDiv.appendChild(img);
             statusDiv.textContent = 'Region captured. Ready to send.';
             // Update the local variable for the currently open popup instance
             capturedData = { type: 'image', content: request.imageDataUrl };
        }
        // No response needed back to background script
    } else if (request.action === "displayTextData" && request.text) {
        // Similar handler for text data if needed later (e.g., from context menu)
        console.log("Received displayTextData message.");
         sessionStorage.setItem('lastCapturedData', JSON.stringify({
            type: 'text',
            content: request.text
        }));
         const previewDiv = document.getElementById('content-preview');
         const statusDiv = document.getElementById('status');
         if (previewDiv && statusDiv) {
             previewDiv.textContent = request.text;
             statusDiv.textContent = 'Text captured. Ready to send.';
             capturedData = { type: 'text', content: request.text };
         }
    }
});

// Check session storage when popup opens to potentially restore last captured data
document.addEventListener('DOMContentLoaded', () => {
     const lastDataStr = sessionStorage.getItem('lastCapturedData');
     if (lastDataStr) {
         try {
             const lastData = JSON.parse(lastDataStr);
             capturedData = lastData; // Restore for the send button

             const previewDiv = document.getElementById('content-preview');
             const statusDiv = document.getElementById('status');

             if (lastData.type === 'image' && previewDiv) {
                 const img = document.createElement('img');
                 img.src = lastData.content;
                 previewDiv.innerHTML = '';
                 previewDiv.appendChild(img);
                 if(statusDiv) statusDiv.textContent = 'Last captured region loaded. Ready to send.';
             } else if (lastData.type === 'text' && previewDiv) {
                  previewDiv.textContent = lastData.content;
                  if(statusDiv) statusDiv.textContent = 'Last captured text loaded. Ready to send.';
             }
         } catch (e) {
             console.error("Error parsing sessionStorage data:", e);
             sessionStorage.removeItem('lastCapturedData'); // Clear invalid data
         }
     }
});
