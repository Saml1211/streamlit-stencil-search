# MCP Server for Visio Bridge - Technical Architecture

This document describes the technical architecture of the MCP server implementation for Visio Bridge integration.

## System Architecture

The MCP server for Visio Bridge follows a layered architecture that bridges between MCP clients and the existing local HTTP API:

```
┌─────────────────────────┐
│      MCP Client         │ (e.g., Claude for Desktop)
└───────────┬─────────────┘
            │ MCP Protocol (JSON-RPC 2.0)
┌───────────▼─────────────┐
│    MCP Server Layer     │ Implements MCP protocol
├─────────────────────────┤
│    Tool Definitions     │ Defines available tools
├─────────────────────────┤
│    Bridge Layer         │ HTTP client for local API
└───────────┬─────────────┘
            │ HTTP/JSON
┌───────────▼─────────────┐
│    Local API Server     │ FastAPI on port 5100
├─────────────────────────┤
│    Visio Integration    │ PyWin32 COM automation
└───────────┬─────────────┘
            │ COM
┌───────────▼─────────────┐
│    Microsoft Visio      │
└─────────────────────────┘
```

## Component Details

### 1. MCP Server Layer

**Implementation**: `visio_bridge_server.py`

This layer is responsible for:
- Implementing the Model Context Protocol
- Handling JSON-RPC message parsing and formatting
- Managing server lifecycle (initialization, shutdown)
- Registering tool definitions
- Processing tool invocations

**Key Technologies**:
- Python MCP SDK (`mcp` package)
- JSON-RPC 2.0
- Asyncio for asynchronous processing

### 2. Tool Definitions

**Implementation**: Tool functions in `visio_bridge_server.py`

This component defines the tools exposed by the MCP server:
- Tool names, descriptions, and parameter schemas
- Input validation and type checking
- Result formatting and error handling

**Design Patterns**:
- Decorator pattern for tool registration
- Factory pattern for tool result creation

### 3. Bridge Layer

**Implementation**: `make_api_request` function in `visio_bridge_server.py`

This layer handles communication with the local API server:
- HTTP request formation and sending
- Response parsing and error handling
- Timeout management
- Logging of API interactions

**Key Technologies**:
- HTTPX for async HTTP requests
- JSON for data serialization/deserialization

### 4. Local API Server

**Implementation**: Existing FastAPI server in `local-api-server/main.py`

This component provides:
- RESTful API endpoints for Visio operations
- Stencil database access
- Shape search functionality
- Visio COM automation bridge

## Data Flow

### Tool Invocation Flow

1. **Client Request**: MCP client sends a tool invocation request
2. **Server Processing**:
   - MCP server receives and parses the request
   - Validates tool name and parameters
   - Calls the appropriate tool function
3. **Bridge Communication**:
   - Tool function prepares data for the local API
   - Sends HTTP request to the local API
   - Receives and processes the response
4. **Result Formation**:
   - Formats the result as a tool result object
   - Handles any errors that occurred
5. **Client Response**: MCP server sends the result back to the client

### Error Handling Flow

1. **Error Detection**:
   - Protocol errors (invalid requests, unknown tools)
   - Network errors (API unavailable, timeouts)
   - Application errors (Visio not running, operation failed)
2. **Error Processing**:
   - Log the error with details
   - Format an appropriate error message
3. **Error Response**:
   - For protocol errors: Return JSON-RPC error object
   - For tool execution errors: Return tool result with `isError: true`

## Design Decisions

### 1. Asynchronous Processing

**Decision**: Use asyncio for all operations

**Rationale**:
- Allows handling multiple concurrent tool invocations
- Prevents blocking during HTTP requests
- Aligns with MCP SDK's async design

### 2. Separation of Concerns

**Decision**: Separate MCP protocol handling from API communication

**Rationale**:
- Improves maintainability
- Allows independent testing of components
- Makes it easier to update either layer

### 3. Comprehensive Error Handling

**Decision**: Implement detailed error handling at all layers

**Rationale**:
- Provides clear feedback to users
- Facilitates debugging
- Prevents cascading failures

### 4. Configuration Externalization

**Decision**: Use external configuration file

**Rationale**:
- Allows changing settings without code modifications
- Supports different environments (dev, prod)
- Enables user customization

## Security Considerations

### 1. Local-Only Operation

The MCP server is designed to run locally and communicate only with the local API server. It does not expose any network services beyond what's required for MCP communication.

### 2. User Consent

All tool invocations require user consent in Claude for Desktop, ensuring that users maintain control over what operations are performed.

### 3. Input Validation

All tool inputs are validated before processing to prevent injection attacks or other security issues.

### 4. Rate Limiting

The server implements rate limiting to prevent abuse and protect system resources.

## Performance Considerations

### 1. Connection Pooling

The HTTP client uses connection pooling to reduce the overhead of establishing new connections for each request.

### 2. Timeout Management

All HTTP requests have configurable timeouts to prevent hanging operations.

### 3. Asynchronous Processing

Async operations allow the server to handle multiple requests efficiently without blocking.

## Extensibility

The architecture is designed to be easily extensible:

### 1. Adding New Tools

New tools can be added by simply defining new functions with the `@mcp.tool()` decorator and implementing the appropriate logic.

### 2. Supporting New Capabilities

The server can be extended to support additional MCP capabilities (like resources or prompts) by implementing the corresponding protocol handlers.

### 3. Enhanced Bridge Functionality

The bridge layer can be extended to support additional API endpoints or communication patterns.

## Testing Strategy

### 1. Unit Testing

Individual components (tools, bridge layer) can be tested in isolation using mock objects.

### 2. Integration Testing

The `test_server.py` script tests the integration between the MCP server and the local API.

### 3. End-to-End Testing

Manual testing with Claude for Desktop verifies the complete flow from user request to Visio operation.

## Deployment Considerations

### 1. Dependencies

The server requires Python 3.10+ and the MCP SDK, which should be installed in a virtual environment.

### 2. Configuration

The server uses a configuration file for settings like API URL, timeouts, and logging levels.

### 3. Startup Scripts

Convenience scripts (`start_server.bat`, `start_server.sh`) are provided for easy startup on different platforms.

## Future Enhancements

### 1. Authentication

Add optional authentication for the MCP server to prevent unauthorized access.

### 2. Caching

Implement caching for frequently used data (like stencil lists) to improve performance.

### 3. Metrics and Monitoring

Add metrics collection and monitoring capabilities to track server health and usage.

### 4. Advanced Tool Capabilities

Extend tools with features like progress reporting, cancellation, and streaming results.
