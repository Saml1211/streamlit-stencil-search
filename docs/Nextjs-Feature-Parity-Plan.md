# Next.js Feature Parity Plan

## Goal
Implement all core features of the Streamlit Visio Stencil Search application in the Next.js frontend to achieve feature parity. The Next.js UI is assumed to be using shadcn/ui. Visio integration features are considered essential.

## Revised Plan

### Phase 1: Core Features (excluding Shape Preview)
- **Objective:** Implement the fundamental missing features required for core application functionality.
  - Implement the UI for setting and managing directory paths for scanning. This might involve a dedicated section on the Settings page or a modal/dialog.
  - Add functionality to add shapes to collections from the main search results page (and possibly the shape detail modal).

### Phase 2: Additional Tools & Health Monitor
- **Objective:** Implement the dedicated tools and enhance existing pages with missing functionality.
  - Create a dedicated page/section for the "Temp File Cleaner" feature, including UI for scanning, listing, and removing temporary files.
  - Enhance the "System Status" page to become a full "Stencil Health Monitor". This involves fetching and displaying analytical data about stencils (e.g., empty stencils, duplicates, issues) and potentially including data visualizations (charts, graphs).
  - Implement the "Export Capabilities" feature, allowing users to export search results and potentially health reports in various formats (CSV, Excel, TXT). This will require backend endpoints and frontend UI for selecting format and triggering export.

### Phase 3: Visio Integration, Advanced Features, and Shape Preview
- **Objective:** Implement the essential Visio integration features, advanced functionalities, and the shape preview.
  - Implement the UI and logic for direct Visio integration features, such as searching within the currently open Visio document and importing selected shapes directly into Visio.
  - Implement UI and logic for detecting multiple open Visio sessions and allowing the user to select an "active" session.
  - Implement "Advanced Filtering" UI on the main search page, allowing users to filter results by metadata or properties.
  - Implement the Shape Preview rendering on the main search page.
  - (Stretch Goal/Lower Priority): Implement UI for "Remote Visio Connectivity", "Multi-document Support" (if different from session selection), and "Shape Editing" if deemed necessary for full parity and if the backend supports these via the MCP server.
  - *Throughout this phase, MCP tools, such as the MCP Inspector, will be utilized for testing and validating interactions with the backend API and MCP server.*

### Phase 4: Refinement and Testing
- **Objective:** Polish the implemented features, ensure responsiveness, and perform thorough testing.
  - Review and refine the UI and user experience for all implemented features.
  - Ensure the application is fully responsive across different screen sizes.
  - Conduct comprehensive testing of all features, comparing behavior and results to the Streamlit version.
  - Address any bugs or performance issues identified during testing.
  - Update documentation (Memory Bank, READMEs) to reflect the implemented features in the Next.js frontend.

```mermaid
graph TD
    A[Start Planning] --> B(Gather Info: Streamlit Features);
    A --> C(Gather Info: Next.js State);
    B --> D{Compare Features};
    C --> D;
    D --> E[Identify Missing Features];
    E --> F[Phase 1: Core Features];
    F --> G[Phase 2: Additional Tools];
    G --> H[Phase 3: Visio & Advanced & Preview];
    H --> I[Phase 4: Refinement & Testing];
    I --> J{Plan Complete?};
    J -- Yes --> K[Present Plan];
    J -- No --> E; % Loop back if more refinement needed
    K --> L(User Review);
    L -- Approved --> M[Proceed to Implementation Mode];
    L -- Revise --> F; % Loop back to refine plan