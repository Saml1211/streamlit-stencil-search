# New Features Documentation

This document provides detailed information about the new features added to the Visio Stencil Explorer application.

## Table of Contents
- [Shape Preview Enhancements](#shape-preview-enhancements)
- [Shape Metadata Filtering](#shape-metadata-filtering)
- [Enhanced Visio Integration](#enhanced-visio-integration)
- [User Customization Options](#user-customization-options)
- [Improved Debugging Capabilities](#improved-debugging-capabilities)

## Shape Preview Enhancements

The shape preview system has been completely redesigned to extract and use actual shape geometry data from Visio files, rather than generating generic shapes based on the shape name.

### Key Improvements

- **Accurate Visual Representation**: Shape previews now reflect the actual appearance of the shape in Visio.
- **Geometry Extraction**: The application extracts geometry data from Visio XML files, including paths, lines, arcs, and other elements.
- **Fallback Mechanism**: If geometry data can't be extracted, the system falls back to the previous name-based preview generation.

### Technical Implementation

- Enhanced `stencil_parser.py` to extract shape geometry data from Visio files
- Updated `shape_preview.py` to use this geometry data to generate accurate previews
- Added error handling for cases where geometry data can't be extracted

## Shape Metadata Filtering

The application now extracts and stores additional metadata about shapes, allowing users to filter search results based on shape properties.

### Available Metadata Filters

- **Dimensions**: Filter shapes by width and height
- **Properties**: Filter shapes that have custom properties
- **Property Values**: Search for shapes with specific property name/value pairs

### UI Enhancements

- Added metadata filter controls in the sidebar
- Added option to display metadata columns in search results
- Enhanced shape preview panel to display shape properties

### Technical Implementation

- Updated database schema to store shape dimensions and properties
- Modified search function to support filtering by metadata
- Added UI elements for metadata filtering and display

## Enhanced Visio Integration

The Visio integration code has been improved to handle errors more gracefully and to work better across different platforms.

### Key Improvements

- **Specific COM Error Handling**: Added detailed error handling for COM errors with specific error codes and messages
- **Path Normalization**: Implemented cross-platform path handling to ensure paths scanned on macOS are correctly interpreted when interacting with Visio on Windows
- **Detailed Logging**: Added comprehensive logging for easier debugging of integration issues

### Technical Implementation

- Added specific error handling for COM errors in `visio_integration.py`
- Implemented path normalization to handle cross-platform path differences
- Added detailed logging for easier debugging of integration issues

## User Customization Options

The application now supports user preferences through the configuration file.

### Available Customization Options

- **Default Startup Directory**: Configure the directory that is automatically loaded when the application starts
- **Default Search Mode**: Set whether the application should use FTS (Full-Text Search) or standard search by default
- **Default Result Limit**: Configure the maximum number of search results to display
- **Show Metadata Columns**: Choose whether to display metadata columns in search results by default

### Technical Implementation

- Updated `config.yaml` to include new user preference settings
- Modified `app.py` to read these settings and apply them to the UI
- Updated the UI to use these settings

## Improved Debugging Capabilities

The application now includes a comprehensive logging system to help diagnose issues.

### Key Features

- **Configurable Log Levels**: Set the log level (debug, info, warning, error, critical) in the configuration file
- **File Logging**: Logs are saved to the `logs` directory for later analysis
- **Structured Logging**: Logs include timestamps, component names, and log levels
- **Global Exception Handling**: Unhandled exceptions are logged for easier debugging

### Technical Implementation

- Added `logging_utils.py` module for centralized logging configuration
- Updated application code to use the logging system
- Added global exception handler to catch and log unhandled exceptions
