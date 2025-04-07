// Content script that listens for messages to get the current user selection.
// Will be injected into pages on demand or via manifest in future steps.

console.log("Visio Importer Content Script Loaded");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getSelectedText") {
        const selectedText = window.getSelection().toString();
        console.log("Content Script sending selected text:", selectedText);
        sendResponse({ selectedText: selectedText });
        return true; // Keep message channel open for async response if needed.
    }
    // For other actions: extend here
});