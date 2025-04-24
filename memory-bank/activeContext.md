# Active Context: Visio Bridge Integration Suite (Updated: 2025-04-24)

## Current Work Focus
- Planning Next.js frontend feature parity with the Streamlit application.
- Debugging the core Streamlit application (`streamlit run app.py`).
- Specifically addressing `IndentationError`s introduced during previous edits and the original `StreamlitDuplicateElementKey` error on the "Visio Control" page.

## Recent Changes

*   **Next.js Feature Parity Plan**: Created detailed implementation plan for achieving feature parity between Next.js and Streamlit dashboards (`docs/Nextjs-Feature-Parity-Plan.md`).
*   Fixed `IndentationError` in `app/core/components.py`.
*   Fixed `IndentationError` in `modules/Visio_Stencil_Explorer.py`.
*   **Phase 1 Completed (`task-15`):** Visio COM logic for text/image import.
*   **Phase 2 Completed (`task-16`):** FastAPI CORS origins updated.
*   **Phase 3 Completed (`task-17`):** Chrome Extension state persistence via `chrome.storage.local`.
*   **Phase 4 Completed (`task-18`):** MCP server configuration refinement (command-line args).
*   **Phase 5 Setup (`task-19`):** 
    *   Successfully started background servers.
    *   Identified and integrated the **MCP Inspector** tool.
    *   Documented Inspector usage in `memory-bank/techContext.md` and `visio_bridge/README.md`.
    *   Created `start_inspector.bat` for easier launch.

## Active Decisions

*   Prioritizing Next.js feature parity planning while also addressing runtime errors in the Streamlit application.
*   Utilizing MCP Task Manager for planning and tracking implementation of Next.js feature parity.
*   **MCP Server Config:** Command-line arguments remain preferred.
*   **Task Order:** Continuing with dependency-based task order.
*   **Phase 5 Verification:** Using **MCP Inspector** (UI and CLI) as the primary method for verifying MCP server tool functionality, replacing reliance on potentially unreliable direct tool calls or separate manual clients. (Currently paused for Streamlit debugging).

## Current Tasks

*   Verifying the fixes for the `IndentationError`s.
*   Investigating the root cause of the `StreamlitDuplicateElementKey` error, likely related to duplicate widget keys in the Visio integration section of the sidebar rendered by `render_shared_sidebar` in `app/core/components.py`.

## Next Steps (High-Level)

1.  **Next.js Implementation**: Begin implementing the Next.js feature parity plan following the phased approach:
    - **Phase 1**: Core Features (excluding Shape Preview)
    - **Phase 2**: Additional Tools & Health Monitor
    - **Phase 3**: Visio Integration, Advanced Features, and Shape Preview
    - **Phase 4**: Refinement and Testing
2.  **Run Streamlit App**: Execute `streamlit run app.py` to confirm indentation fixes and observe if the `StreamlitDuplicateElementKey` error persists.
3.  **Fix Duplicate Key Error**: If the error persists, identify and correct the duplicate `key` assignments in `app/core/components.py` or related modules.
4.  **Resume MCP Inspector Testing (`task-19`)**: Once the Streamlit app is stable, resume testing the `visio-bridge` tools using the Inspector.
5.  **Approve Phase 5 (`task-19`)**: User to approve after successful verification using the Inspector.
6.  **Execute Phase 6 (`task-20`)**: Begin packaging the `local-api-server` using PyInstaller.
7.  Complete remaining tasks from the original plan (`req-4`).

## Technical Considerations

*   Need to ensure unique keys are used for all Streamlit widgets, especially when components are rendered conditionally or reused (e.g., `render_shared_sidebar`). Check usage of `key_prefix`.
*   The `StreamlitDuplicateElementKey` error often arises when the same key is used for widgets within the same script run, potentially due to reruns or conditional rendering logic.
*   Reliability of starting background processes via `run_terminal_cmd` confirmed.
*   **MCP Inspector** provides a more controlled environment for testing MCP interactions, potentially bypassing the `getaddrinfo` issue seen with direct tool calls.
*   PyInstaller packaging for `pywin32` (`task-20`) still requires careful attention.
*   Ensure Node.js/npm prerequisites for `MCP Inspector` are met in the development environment.
*   Next.js implementation should use shadcn/ui for UI components to maintain a consistent look and feel.
*   The Shape Preview feature is technically challenging and has been moved to Phase 3 in the Next.js implementation plan.
*   Visio integration features are considered essential, not optional, for the Next.js implementation.
*   Multiple Visio sessions support needs to be implemented in the Next.js version.
