# System Patterns

## System Architecture
The Visio Stencil Search application follows a modular architecture built on the Streamlit framework. The system is organized into distinct components that handle specific responsibilities, following a clean separation of concerns.

## Architecture Overview
```
streamlit-stencil-search/
├── app/                  # Core application logic
│   └── core/             # Business logic components
├── pages/                # Streamlit pages/views
├── data/                 # Cached stencil data (database)
├── docs/                 # Documentation and images
├── app.py                # Main application entry point
└── requirements.txt      # Python dependencies
```

## Key Components

### Core Business Logic (`app/core/`)
- **Config Management** (`config.py`): Handles application configuration and settings.
- **Database Interface** (`db.py`): Manages the persistent storage and retrieval of stencil data.
- **File Scanner** (`file_scanner.py`): Recursively scans directories for Visio stencils.
- **Stencil Parser** (`stencil_parser.py`): Extracts shape information from stencil files.
- **Shape Preview** (`shape_preview.py`): Generates visual previews of shapes without Visio.
- **Visio Integration** (`visio_integration.py`): Handles Visio-specific file operations.

### User Interface (`pages/`)
- **Visio Stencil Explorer** (`01_Visio_Stencil_Explorer.py`): Main search interface.
- **Temp File Cleaner** (`02_Temp_File_Cleaner.py`): Tool for finding and removing temp files.
- **Stencil Health** (`03_Stencil_Health.py`): Tool for analyzing stencil health issues.

### Application Entry Point (`app.py`)
- Configures the Streamlit application
- Sets up page navigation
- Initializes app-wide services and configuration

## Design Patterns

### Data Flow Pattern
1. **Scan Phase**: The File Scanner locates all Visio files in specified directories
2. **Parse Phase**: The Stencil Parser extracts shape information from each file
3. **Storage Phase**: The Database Interface stores the extracted data
4. **Query Phase**: The UI components query the database based on user input
5. **Display Phase**: Results are formatted and displayed to the user

### Component Communication
- Components communicate through well-defined interfaces
- Core business logic is decoupled from UI components
- Data is passed between components using standard Python data structures
- Configuration is centralized and accessible to all components

### State Management
- Streamlit session state is used for maintaining application state
- Persistent data is stored in the data directory
- Configuration is stored in a YAML file (config.yaml)

## Technical Decisions

### Framework Choice
- **Streamlit**: Selected for rapid development of data applications with minimal frontend code
- Provides built-in components for common UI patterns (sidebar, data tables, file uploaders)
- Enables easy deployment as a local application or web service

### Database Approach
- Using a file-based database for simplicity of deployment
- Structured to optimize for search performance
- Stores metadata about stencils and shapes rather than the files themselves

### Preview Generation
- Custom implementation to render shape previews without requiring Visio
- Balances preview quality with generation speed
- Works across different versions of Visio file formats 