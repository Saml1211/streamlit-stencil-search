# Visio Stencil Search – Next.js Dashboard

## Overview
Visio Stencil Search is a modern web application for cataloging, searching, and managing Microsoft Visio stencil files across network directories. The Next.js dashboard is a full-featured, production-ready frontend built with shadcn/ui and designed for maximum usability, speed, and cross-device support. It achieves feature parity with the classic Streamlit dashboard, and supports direct integration with backend search/database services for high performance.

## Features
- **Network Directory Scanning**: Find all Visio stencil files (.vss, .vssx, .vssm) across local and network shares
- **Real-Time Shape Search**: Instantly search and filter shapes across large stencil collections
- **Shape Collections**: Create shape collections for batch operations and reuse
- **Favorites**: Mark shapes/stencils for rapid access
- **Health Monitor & Temp File Cleaner**: Analyze stencils for issues and remove problematic temp files
- **Export & Reporting**: Export search results and health reports (CSV, Excel, TXT)
- **Visio Integration**: Direct search/import into Visio (when available), including multi-session support
- **Advanced Filtering**: Filter by metadata, properties, dimensions, etc.
- **Modern UI/UX**: Responsive, mobile/touch-friendly, accessible, with smooth navigation and feedback
- **shadcn/ui Components**: Consistent, elegant UI with dark mode and keyboard/touch accessibility

## Quick Start

### Prerequisites
- Node.js (18+ recommended)
- Access to the Python backend/API server (see project root README for backend setup)
- Yarn, npm, or pnpm package manager

### Setup

```sh
cd next-frontend
npm install         # or yarn, pnpm, etc.
npm run dev         # start the development server
```

Visit [http://localhost:3000](http://localhost:3000) to use the dashboard.

### Integrating with Backend
- The Next.js dashboard communicates with the Python backend via REST API (see `/src/api/index.ts` for configuration).
- Ensure the backend is running and accessible from your browser.
- Backend configuration (API endpoint, ports) can be set in the relevant environment files or configuration section.

## Usage

- Use the sidebar (desktop) or menu (mobile) to access Stencil Search, Collections, Favorites, Health Monitor, Settings, and Temp File Cleaner.
- Search, filter, and preview shapes or stencils directly from the dashboard.
- Create, manage, and export shape collections or search results.
- Use the Temp File Cleaner to remove problematic files from your environment.
- Access Visio integration features when running on a compatible Windows system with Visio installed.

## Feature Parity and Known Differences

**Parity:** All core features from the Streamlit dashboard are present and functionally equivalent, including:
- Directory scanning, search, filtering, shape preview (where available), health checks, collections, favorites, and Visio integration features.

**Minor Differences:**
- The Next.js UI is touch/mobile optimized and may present navigation slightly differently.
- Some advanced Streamlit diagnostic/debug panels are not exposed in production Next.js.
- Certain rarely used backend error/status messages may be surfaced in-app notifications rather than sidebar logs.

All discovered differences or limitations are documented in the Memory Bank (see `/memory-bank/activeContext.md` and `/progress.md`).

## Accessibility & Responsive Design

- All screens adapt to desktop, tablet, and mobile layouts.
- Buttons, dialogs, and lists are fully accessible via keyboard and screen reader.
- Touch controls, swipe navigation, and drag/drop (where appropriate) are supported on mobile.

## Troubleshooting

- If you see blank results, verify backend connection settings.
- For Visio integration, ensure the backend server is running on a compatible Windows system with Visio installed and the appropriate permissions granted.
- For bug reports or requests, see the main project README.

## Documentation & Further Information

- [Project Status](../docs/project_status.md)
- [Feature Parity Plan](../docs/Nextjs-Feature-Parity-Plan.md)
- [Memory Bank Documentation](../memory-bank/)
- [New Features and Technical Notes](../docs/new_features.md)

For backend/server setup, deployment, and advanced integration, see the root README and docs in the main repo.

---

© 2025 Visio Stencil Search Team
