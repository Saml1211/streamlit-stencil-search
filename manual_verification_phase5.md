# Manual Verification Steps for Phase 5: Test and Configure Remote/Local Setup (Task task-19)

**Objective:** Confirm that the MCP server can successfully communicate with the Local API server and trigger Visio actions.

**Prerequisites:**

1.  The `local-api-server` process should be running in the background (started via `run_terminal_cmd F:\REPOSITORIES\...\local-api-server; $env:VISIO_BRIDGE_API_KEY='test-key-for-phase5'; .\venv\Scripts\python.exe main.py`).
2.  The `mcp-server` process should be running in the background (started via `run_terminal_cmd F:\REPOSITORIES\...\mcp-server; .\venv\Scripts\python.exe visio_bridge_server.py --url http://127.0.0.1:5100 --api-key test-key-for-phase5`).
3.  Microsoft Visio should be running on the same machine as the `local-api-server`.
4.  Your MCP Client (e.g., Claude Desktop) should be configured to connect to the `visio-bridge` MCP server as outlined previously.

**Verification Steps:**

1.  **Connect MCP Client:** Ensure your MCP client (e.g., Claude Desktop) is running and has successfully connected to the `visio-bridge` server.

2.  **Run Connection Check:**
    *   Ask your MCP client to execute the following tool call:
        ```
        check_visio_connection
        ```
    *   **Expected Result:** The client should return a message similar to: `Visio Bridge API is running and ready to accept commands.`
    *   **If it fails:** Note the error message. It might indicate issues with the client configuration, the running MCP server process, or potentially still a connection issue despite earlier checks.

3.  **Run Text Import Test:**
    *   Ask your MCP client to execute the following tool call:
        ```
        import_text_to_visio(text_content="Manual Test Successful")
        ```
    *   **Expected Result:**
        *   The client should return a message like: `Successfully imported text to Visio. Shape ID: <some_number>`
        *   Check the active Visio document on the machine running the `local-api-server`. A new shape containing the text "Manual Test Successful" should have appeared (likely near the center of the page).
    *   **If it fails:** Note the error message returned by the client. Check the console/logs of the `local-api-server` and `mcp-server` (if accessible) for more detailed errors (e.g., COM errors).

4.  **(Optional) Run Image Import Test:**
    *   Obtain a small Base64 encoded image string (e.g., from an online converter, or use a known small one like `data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7` which is a 1x1 transparent pixel).
    *   Ask your MCP client to execute the following tool call (replace `<base64_string>`):
        ```
        import_image_to_visio(image_data="<base64_string>")
        ```
    *   **Expected Result:**
        *   The client should return a message like: `Successfully imported image to Visio. Shape ID: <some_number>`
        *   Check the active Visio document. A new shape containing the imported image should have appeared.
    *   **If it fails:** Note the error message and check server logs.

**Completion:**

*   If steps 1-3 (and optionally 4) succeed without errors, Phase 5 can be considered verified.
*   Return to the chat and state that verification was successful, then approve Task `task-19`.
*   If any step fails, report the specific step and any error messages encountered. 