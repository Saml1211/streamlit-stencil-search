// Script for popup.html logic

console.log("Popup script loaded.");

// Global-like variable to hold captured data (text or image data URL)
// Will be loaded from chrome.storage.local on popup open
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
        // Clear stored data as well when initiating a new capture
        chrome.storage.local.remove('lastCapturedData', () => {
            console.log('Cleared previous captured data from storage.');
        });

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
        // Now relies on capturedData being loaded from storage or set by message listener
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
                   // Clear storage after successful send
                   chrome.storage.local.remove('lastCapturedData', () => {
                       console.log('Cleared captured data from storage after sending.');
                   });
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
        const dataToStore = {
            type: 'image',
            content: request.imageDataUrl
        };

        // Store data using chrome.storage.local
        chrome.storage.local.set({ 'lastCapturedData': dataToStore }, () => {
            if (chrome.runtime.lastError) {
                console.error("Error saving captured image data to storage:", chrome.runtime.lastError);
            } else {
                console.log("Captured image data saved to storage.");
                // Update the local variable immediately for the currently open popup instance
                capturedData = dataToStore;
            }
        });

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
        const dataToStore = {
            type: 'text',
            content: request.text
        };
        // Store data using chrome.storage.local
        chrome.storage.local.set({ 'lastCapturedData': dataToStore }, () => {
             if (chrome.runtime.lastError) {
                 console.error("Error saving captured text data to storage:", chrome.runtime.lastError);
             } else {
                 console.log("Captured text data saved to storage.");
                 // Update the local variable immediately for the currently open popup instance
                 capturedData = dataToStore;
             }
         });

         const previewDiv = document.getElementById('content-preview');
         const statusDiv = document.getElementById('status');
         if (previewDiv && statusDiv) {
             previewDiv.textContent = request.text;
             statusDiv.textContent = 'Text captured. Ready to send.';
             capturedData = { type: 'text', content: request.text };
         }
    }
});

// Check chrome.storage.local when popup opens to potentially restore last captured data
document.addEventListener('DOMContentLoaded', () => {
    const previewDiv = document.getElementById('content-preview');
    const statusDiv = document.getElementById('status');

    chrome.storage.local.get('lastCapturedData', (result) => {
        if (chrome.runtime.lastError) {
            console.error("Error retrieving data from storage:", chrome.runtime.lastError);
            return;
        }

        const lastData = result.lastCapturedData;

        if (lastData) {
            console.log("Restoring captured data from storage:", lastData.type);
            capturedData = lastData; // Restore for the send button

            if (lastData.type === 'image' && previewDiv) {
                const img = document.createElement('img');
                img.src = lastData.content;
                previewDiv.innerHTML = '';
                previewDiv.appendChild(img);
                if (statusDiv) statusDiv.textContent = 'Last captured region loaded. Ready to send.';
            } else if (lastData.type === 'text' && previewDiv) {
                previewDiv.textContent = lastData.content;
                if (statusDiv) statusDiv.textContent = 'Last captured text loaded. Ready to send.';
            }
        } else {
            console.log("No previous captured data found in storage.");
        }
    });
});
