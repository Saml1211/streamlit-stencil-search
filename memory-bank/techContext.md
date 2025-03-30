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
- **Matplotlib (3.7.0+)**: Visualization for health analysis
- **NumPy (1.24.0+)**: Numerical processing
- **TQDM (4.66.0+)**: Progress bar for long-running operations
- **Python-dotenv (1.0.0+)**: Environment variable management
- **XlsxWriter (3.1.0+)**: Excel export functionality
- **PyWin32 (302+)**: Windows API access (optional, for Windows-specific features)
- **SQLite3**: Database functionality (included in Python standard library)

## Development Environment

### Requirements
- **Python 3.8+**: Required for running the application
- **Git**: Recommended for version control
- **IDE**: Any Python-compatible IDE (VSCode, PyCharm, etc.)

### Local Setup
1. Clone the repository
2. Install dependencies using `pip install -r requirements.txt`
3. Run the application with `streamlit run app.py`

### Development Workflow
- Local development and testing
- Changes committed to Git repository
- No formal CI/CD pipeline specified

## Technical Constraints

### Platform Compatibility
- **Cross-Platform**: The core application is designed to run on Windows, macOS, and Linux
- **Windows-Specific Features**: Some features may utilize PyWin32 and are Windows-only
- **Browser-Based UI**: Application interface runs in any modern web browser

### Performance Considerations
- **Memory Usage**: Scanning large directories with many stencils can be memory-intensive
- **Database Size**: The application creates a local database to store stencil information
- **Search Performance**: Optimized for fast text search across many stencils

### Security and Access
- **Local Application**: Primarily designed as a locally-run application
- **Network Access**: Can be configured to access network shares for scanning stencils
- **No Authentication**: No built-in user authentication system

## File Formats

### Supported Visio Formats
- **.vss**: Visio Stencil file (legacy binary format)
- **.vssx**: Visio Stencil file (Office Open XML format)
- **.vssm**: Visio Macro-enabled Stencil file

### Internal Data Storage
- **SQLite Database**: Used for storing stencil and shape metadata
- **YAML Configuration**: Used for application settings
- **JSON Data**: Used for certain cached data structures 