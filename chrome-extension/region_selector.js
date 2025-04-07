// Content script injected to handle region selection for screenshots

(function() {
    console.log("Region Selector Script Injected.");

    let startX, startY, overlayDiv, selectionDiv;
    let isSelecting = false;

    // Cleanup function to remove elements and listeners
    function cleanup() {
        console.log("Cleaning up region selector UI.");
        if (overlayDiv) overlayDiv.remove();
        if (selectionDiv) selectionDiv.remove();
        document.removeEventListener('mousedown', handleMouseDown);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'default'; // Restore cursor
    }

    // Create overlay div
    overlayDiv = document.createElement('div');
    overlayDiv.style.position = 'fixed';
    overlayDiv.style.top = '0';
    overlayDiv.style.left = '0';
    overlayDiv.style.width = '100vw';
    overlayDiv.style.height = '100vh';
    overlayDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.3)'; // Semi-transparent overlay
    overlayDiv.style.zIndex = '9999998'; // High z-index
    overlayDiv.style.cursor = 'crosshair';
    document.body.appendChild(overlayDiv);

    // Create selection div (initially hidden)
    selectionDiv = document.createElement('div');
    selectionDiv.style.position = 'absolute';
    selectionDiv.style.border = '2px dashed #fff'; // Dashed white border
    selectionDiv.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'; // Slightly visible selection
    selectionDiv.style.zIndex = '9999999'; // Above overlay
    selectionDiv.style.display = 'none'; // Hide initially
    document.body.appendChild(selectionDiv);

    document.body.style.cursor = 'crosshair'; // Change cursor for selection

    // Mouse Down: Start selection
    function handleMouseDown(e) {
        // Prevent starting selection on existing elements like scrollbars
        if (e.target !== overlayDiv) return;

        isSelecting = true;
        startX = e.clientX;
        startY = e.clientY;

        selectionDiv.style.left = startX + 'px';
        selectionDiv.style.top = startY + 'px';
        selectionDiv.style.width = '0px';
        selectionDiv.style.height = '0px';
        selectionDiv.style.display = 'block'; // Show selection div

        e.preventDefault(); // Prevent default text selection behavior
    }

    // Mouse Move: Resize selection rectangle
    function handleMouseMove(e) {
        if (!isSelecting) return;

        const currentX = e.clientX;
        const currentY = e.clientY;

        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);
        const left = Math.min(currentX, startX);
        const top = Math.min(currentY, startY);

        selectionDiv.style.left = left + 'px';
        selectionDiv.style.top = top + 'px';
        selectionDiv.style.width = width + 'px';
        selectionDiv.style.height = height + 'px';
    }

    // Mouse Up: Finalize selection and send coordinates
    function handleMouseUp(e) {
        if (!isSelecting) return;
        isSelecting = false;

        const endX = e.clientX;
        const endY = e.clientY;

        const finalLeft = Math.min(startX, endX);
        const finalTop = Math.min(startY, endY);
        const finalWidth = Math.abs(endX - startX);
        const finalHeight = Math.abs(endY - startY);

        // Only send if a meaningful area was selected
        if (finalWidth > 5 && finalHeight > 5) {
            const coords = {
                x: finalLeft + window.scrollX, // Account for page scroll
                y: finalTop + window.scrollY,
                width: finalWidth,
                height: finalHeight,
                devicePixelRatio: window.devicePixelRatio // Important for accurate cropping on high-DPI screens
            };
            console.log("Region selected:", coords);
            // Send coordinates back to the background script
            chrome.runtime.sendMessage({ action: "regionSelected", coords: coords }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error("Error sending region coordinates:", chrome.runtime.lastError.message);
                } else {
                    console.log("Region coordinates sent, response:", response);
                }
                cleanup(); // Clean up UI regardless of response
            });
        } else {
            console.log("Selection too small, cancelled.");
            cleanup(); // Clean up if selection was too small or just a click
        }
        e.preventDefault();
    }

    // Add listeners
    document.addEventListener('mousedown', handleMouseDown, true); // Use capture phase if needed
    document.addEventListener('mousemove', handleMouseMove, true);
    document.addEventListener('mouseup', handleMouseUp, true);

    // Optional: Add Escape key listener to cancel selection
    document.addEventListener('keydown', function handleEscape(e) {
        if (e.key === 'Escape') {
            console.log("Region selection cancelled by Escape key.");
            cleanup();
            document.removeEventListener('keydown', handleEscape); // Remove self
        }
    });

})(); // IIFE to avoid polluting global scope