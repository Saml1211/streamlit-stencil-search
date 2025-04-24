# System Patterns

## System Architecture
The Visio Stencil Search application follows a modular architecture with dual frontend implementations: the primary Streamlit-based dashboard and a new Next.js-based dashboard. Both frontends interact with the same backend services, following a clean separation of concerns. This dual-UI approach provides flexibility while maintaining consistent functionality.

## Architecture Overview
```
streamlit-stencil-search/
├── app/                  # Core application logic (Streamlit)
│   ├── core/             # Business logic components
│   └── data/             # Application data resources
├── pages/                # Streamlit pages/views
├── data/                 # Cached stencil data (database)
├── docs/                 # Documentation and images
├── memory-bank/          # Project documentation and progress tracking
├── logs/                 # Application logs
├── temp/                 # Temporary file storage
├── app.py                # Main Streamlit application entry point
├── config.yaml           # Configuration settings
├── requirements.txt      # Python dependencies
├── next-frontend/        # Next.js frontend implementation
│   ├── src/              # Next.js source code
│   │   ├── app/          # Next.js app router pages
│   │   ├── components/   # React components
│   │   ├── lib/          # Utility functions
│   │   └── api/          # API client code
│   ├── public/           # Static assets
│   └── package.json      # Node.js dependencies
└── mcp-server/           # Model Context Protocol server
```

## Key Components

### Core Business Logic (`app/core/`)
- **Config Management** (`config.py`): Handles application configuration and settings using YAML.
- **Database Interface** (`db.py`): Manages the persistent storage and retrieval of stencil data with SQLite and FTS5.
- **File Scanner** (`file_scanner.py`): Recursively scans directories for Visio stencils.
- **Stencil Parser** (`stencil_parser.py`): Extracts shape information from stencil files using ZIP/XML parsing.
- **Shape Preview** (`shape_preview.py`): Generates visual previews of shapes without Visio using matplotlib.
- **Visio Integration** (`visio_integration.py`): Handles Visio-specific file operations and live document integration using COM automation.
- **Custom Styles** (`custom_styles.py`): Provides enhanced UI styling and layout improvements.
- **Reusable Components** (`components.py`): Contains shared UI components used across pages.
- **Logging Utilities** (`logging_utils.py`): Handles application logging with configurable levels.

### User Interface (`pages/`)
- **Visio Stencil Explorer** (`01_Visio_Stencil_Explorer.py`): Main search interface.
- **Temp File Cleaner** (`02_Temp_File_Cleaner.py`): Tool for finding and removing temp files.
- **Stencil Health** (`03_Stencil_Health.py`): Tool for analyzing stencil health issues.
- **Visio Control** (`04_Visio_Control.py`): Interface for direct Visio integration.

### Application Entry Point (`app.py`)
- Configures the Streamlit application
- Sets up page navigation with icons
- Initializes app-wide services and configuration
- Applies custom CSS styles
- Injects JavaScript for responsive design
- Initializes database and checks integrity
- Sets up error handling and logging
- Manages session state initialization

## Design Patterns

### Data Flow Pattern
1. **Scan Phase**: The File Scanner locates all Visio files in specified directories
2. **Parse Phase**: The Stencil Parser extracts shape information from each file
3. **Storage Phase**: The Database Interface stores the extracted data in SQLite
4. **Query Phase**: The UI components query the database based on user input
5. **Display Phase**: Results are formatted and displayed to the user
6. **Interaction Phase**: User can interact with results via preview, collection, or Visio integration

### Component Communication
- Components communicate through well-defined interfaces
- Core business logic is decoupled from UI components
- Data is passed between components using standard Python data structures
- Configuration is centralized and accessible to all components
- Session state is used to maintain consistent state across pages
- Error handling is implemented at appropriate abstraction levels

### State Management
- Streamlit session state is used for maintaining application state
- Persistent data is stored in SQLite database
- Configuration is stored in a YAML file (config.yaml)
- Directory presets are stored in the database
- Favorites and search history are persisted between sessions
- Error state is handled with appropriate user feedback
- Background processing state is tracked to prevent conflicts

### Error Handling Pattern
- Global exception handler for unhandled exceptions
- Component-level error handling with graceful degradation
- User-friendly error messages with appropriate context
- Database integrity checking with automatic repair mechanisms
- Logging of errors for debugging and troubleshooting
- Fallback mechanisms for critical components

### UI Layout Patterns
- **Responsive Design**: Layout adapts based on screen dimensions with JavaScript detection
- **Three-Column Layout**: For desktop displays (sidebar, main content, detail panel)
- **Vertical Stacking**: For mobile displays
- **Visual Containers**: Using borders and backgrounds to group related elements
- **Progressive Disclosure**: Using expanders to hide advanced options
- **Consistent Navigation**: Sidebar for global navigation and settings
- **Data Visualization**: Charts to display shape distribution statistics
- **Informative Feedback**: Status messages guide users through the workflow
- **Clear Visual Hierarchy**: Heading sizes and spacing guide the user's attention
- **Collapsible Sections**: Using expanders for optional content
- **Modal Dialogs**: For shape previews and confirmation prompts
- **Card-Based Layout**: Using bordered containers for content organization
- **Tabbed Interfaces**: For organizing related functionality
- **Consistent Spacing**: Maintaining visual rhythm with standardized spacing

### Database Patterns
- **Repository Pattern**: Database class encapsulates all data access logic
- **Connection Pooling**: Connection management for thread safety
- **Transaction Management**: Ensuring data consistency during batch operations
- **Index Optimization**: Strategic indexes for query performance
- **Full-Text Search**: FTS5 virtual tables for text search performance
- **Data Integrity**: Foreign key constraints and integrity checking
- **Migration Strategy**: Versioned database schema changes
- **Backup and Recovery**: Automated backup before potentially destructive operations

## Technical Decisions

### Framework Choices
- **Streamlit**: Selected for rapid development of data applications with minimal frontend code
  - Provides built-in components for common UI patterns (sidebar, data tables, file uploaders)
  - Enables easy deployment as a local application or web service
  - Enhanced with custom CSS for improved visual design
  - Extended with JavaScript for responsive behaviors

- **Next.js**: Selected for a more modern, scalable frontend implementation
  - React-based framework for highly interactive UI
  - Uses shadcn/ui component library for consistent, polished look and feel
  - App Router architecture for improved routing and layout management
  - API routes for backend communication
  - Enhanced SEO capabilities (if needed in the future)

### Database Approach
- Using SQLite database for efficiency and simplicity of deployment
- Optimized with indexes for search performance
- Implemented full-text search (FTS5) for faster text searches
- Added database integrity checking and auto-repair functionality
- Implemented concurrency handling with locks
- Efficient query patterns to minimize memory usage
- Transaction management for data consistency

### Preview Generation
- Custom implementation using matplotlib to render shape previews
- Two-tier approach: geometry-based when available, name-based as fallback
- Geometry parsing from XML data for accurate shape representation
- Caching of generated previews for performance
- Optimized for displaying in the Streamlit interface
- Balanced quality vs. performance considerations

### Visio Integration
- Optional component that enhances functionality when Visio is available
- COM automation using PyWin32 for Windows platforms
- Remote server connection support for distributed environments
- Comprehensive document management (create, save, open)
- Page-level operations (create, rename, navigate)
- Shape manipulation (create, edit, move, resize, align)
- Shape search within documents
- Error handling with graceful degradation
- Clean abstraction layer for Visio operations

### UI Implementation Approaches

#### Streamlit UI
- Using Streamlit's built-in components wherever possible
- Custom HTML/CSS for enhanced styling and layout
- Session state for managing UI state between refreshes
- Standardized input patterns (sliders, date pickers, etc.)
- Data-driven visualization with matplotlib and plotly
- Error handling with appropriate user feedback
- Toggle components for boolean states
- Progress indicators for long-running operations
- Modal shape preview with zooming capability
- Responsive layouts that adapt to browser width
- Card-based design for visual organization
- Consistent spacing and typography

#### Next.js UI
- Component-based architecture with React
- shadcn/ui as the UI component library
- Client-side state management with React hooks
- Server components for improved performance
- Responsive design using CSS modules or tailwindcss
- Consistent design language across all pages
- Progressive enhancement for better user experience
- Modern UI patterns (modals, popovers, etc.)
- Feature parity with Streamlit implementation

### File Handling
- Cross-platform path normalization for compatibility
- Support for network paths and remote file systems
- Asynchronous file operations for responsive UI
- Caching of file metadata for performance
- Efficient XML parsing for Visio file extraction
- Robust error handling for corrupt or inaccessible files 