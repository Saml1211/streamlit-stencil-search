# Technical Context

## Core Technologies

### Programming Language
- **Python 3.8+**: The application is built entirely using Python, targeting version 3.8 and above.

### Framework & Libraries
- **Streamlit (1.29.0+)**: Primary framework for building the web interface
- **Pandas (2.0.0+)**: Used for data manipulation and analysis
- **LXML (4.9.3+)**: XML processing for parsing Visio files
- **PyYAML (6.0+)**: YAML configuration file parsing
- **Pydantic (2.5.0+)**: Data validation and settings management
- **Matplotlib (3.7.0+)**: Visualization for health analysis and shape preview generation
- **Plotly (5.18.0+)**: Advanced data visualization for stencil health analysis
- **NumPy (1.24.0+)**: Numerical processing and data analysis
- **TQDM (4.66.0+)**: Progress bar for long-running operations
- **Python-dotenv (1.0.0+)**: Environment variable management
- **XlsxWriter (3.1.0+)**: Excel export functionality
- **PyWin32 (302+)**: Windows API access for Visio integration via COM
- **SQLite3**: Database functionality (included in Python standard library)
- **Pillow (10.0.0+)**: Image processing for shape previews
- **Threading**: Concurrent processing for background operations

## Development Environment

### Requirements
- **Python 3.8+**: Required for running the application
- **Git**: Recommended for version control
- **IDE**: Any Python-compatible IDE (VSCode, PyCharm, etc.)
- **Microsoft Visio**: Optional for enhanced functionality

### Local Setup
1. Clone the repository
2. Install dependencies using `pip install -r requirements.txt`
3. Run the application with `streamlit run app.py`

### Development Workflow
- Local development and testing
- Changes committed to Git repository
- Memory bank for project documentation and progress tracking
- Comprehensive logging for debugging and monitoring
- Database integrity checks during startup

## Technical Constraints

### Platform Compatibility
- **Cross-Platform**: The core application is designed to run on Windows, macOS, and Linux
- **Windows-Specific Features**: Visio integration features are Windows-only
- **Browser-Based UI**: Application interface runs in any modern web browser

### Performance Considerations
- **Memory Usage**: Scanning large directories with many stencils can be memory-intensive
- **Database Size**: The SQLite database can grow based on the number of stencils and shapes
- **Search Performance**: Optimized with full-text search for fast queries
- **Preview Generation**: Shape preview generation balances quality with performance
- **Concurrent Operations**: Database locks are managed to prevent conflicts
- **Background Processing**: Long-running tasks execute in background threads
- **UI Responsiveness**: JavaScript helps maintain responsive interface during operations

### Security and Access
- **Local Application**: Primarily designed as a locally-run application
- **Network Access**: Can be configured to access network shares for scanning stencils
- **No Authentication**: No built-in user authentication system
- **File System Access**: Requires read access to stencil directories
- **Remote Connection**: Optional remote Visio server connection with DCOM

## File Formats

### Supported Visio Formats
- **.vss**: Visio Stencil file (legacy binary format)
- **.vssx**: Visio Stencil file (Office Open XML format)
- **.vssm**: Visio Macro-enabled Stencil file
- **.vst**: Visio Template file (legacy binary format) 
- **.vstx**: Visio Template file (Office Open XML format)
- **.vsdx**: Visio Drawing file (Office Open XML format)

### Internal Data Storage
- **SQLite Database**: Used for storing stencil and shape metadata
- **FTS5 Index**: Full-text search virtual tables for optimized text search
- **YAML Configuration**: Used for application settings
- **JSON Data**: Used for shape geometry and property serialization
- **CSV/Excel Exports**: Used for exporting search results and reports
- **Logging Files**: Structured logs in the logs directory

### API Integration
- **COM Automation**: Used for optional Visio integration
- **DCOM**: Used for remote Visio server connections
- **File System API**: Used for file scanning and operations
- **SQLite API**: Used for database operations

## Application Structure

### Core Modules
- **File Scanner**: Recursive directory traversal and file detection
- **Stencil Parser**: XML-based parsing of Visio stencil files
- **Database Manager**: SQLite-based data persistence and querying with FTS5
- **Shape Preview**: Stand-alone preview generation without Visio
- **Visio Integration**: Optional COM-based integration with Visio
- **Health Analysis**: Tools for analyzing stencil health and issues
- **UI Components**: Reusable interface components
- **Custom Styling**: CSS and JavaScript for enhanced UI
- **Logging System**: Configurable logging with file and console output
- **Config Management**: YAML-based configuration system

### Data Models
- **Stencil**: Metadata about stencil files including path, name, shape count, and file size
- **Shape**: Individual shape data including name, dimensions, geometry, and properties
- **Geometry**: Vector path data for shape preview generation
- **Health Issue**: Representation of stencil health problems with severity levels
- **Directory Preset**: Saved directory path with name and active status
- **Favorite**: Saved stencil or shape for quick access
- **Search Filter**: Parameters for filtering search results
- **Search History**: Record of previous search queries
- **Shape Collection**: Grouped shapes for batch operations

### Database Schema
- **stencils**: Main stencil metadata table with path as primary key
- **shapes**: Shape information with foreign key to stencil
- **shapes_fts**: Virtual FTS5 table for full-text search
- **preset_directories**: Saved directory paths
- **favorites**: User-marked favorite stencils and shapes
- **saved_searches**: Persistent search queries

### Background Processing
- **Directory Scanning**: Background thread for scanning stencil directories
- **Health Analysis**: Background processing for stencil health checks
- **Database Operations**: Concurrent-safe database access with locks
- **Progress Tracking**: Real-time progress indicators for long operations
- **Error Recovery**: Automatic handling of transient failures 