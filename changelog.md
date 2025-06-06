# Changelog

All notable changes to Signal Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-12-11

### 🚀 Added
- **HTTP Streamable Transport Support** - Full production-ready HTTP transport using FastMCP
- **Dual Transport Architecture** - Server and agent now support both stdio and HTTP transports
- **Enhanced Justfile Workflow** - Comprehensive task automation with dedicated HTTP commands
- **Transport Selection** - Runtime transport switching via command-line arguments
- **Production Deployment** - HTTP server ready for distributed MSP environments

### 🔧 Enhanced
- **Server Implementation** - Dual transport server with FastMCP and official MCP SDK
- **Agent Client** - Transport-agnostic client supporting both stdio and HTTP streamable
- **Main Orchestrator** - Enhanced orchestration with transport-aware startup timing
- **Documentation** - Updated README with HTTP usage examples and testing instructions
- **Development Workflow** - Improved justfile with separate HTTP and stdio commands

### 🐛 Fixed
- **Type Annotations** - Resolved Pylance compatibility issues with Optional and List types
- **MCP Protocol** - Proper content response handling for different MCP transport types
- **Transport Handshake** - Fixed connection initialization for both transport modes
- **Error Handling** - Enhanced error reporting with transport-specific debugging

### 📋 Technical Details
- Added `mcp.server.fastmcp.FastMCP` integration for HTTP transport
- Implemented `streamablehttp_client` support in agent
- Enhanced argument parsing with `--transport` and `--server-url` options
- Updated project structure to support dual transport patterns
- Improved logging and debugging for transport-specific operations

### 🎯 Migration Notes
- Existing stdio workflows remain unchanged (backwards compatible)
- New HTTP workflows available via `--transport http` flag
- Justfile commands updated: use `just run-server-http` for production mode
- Default transport remains stdio for development compatibility

---

## [1.0.0] - 2024-12-11

### 🎉 Initial Release

### ✨ Features
- **Standards-Compliant MCP Implementation** - Built with official MCP SDK
- **Intelligent Failure Event Analysis** - Multi-stage processing pipeline
- **Production-Ready Architecture** - Comprehensive error handling and validation
- **Modern Python Tooling** - uv dependency management and justfile automation

### 🧠 Analysis Pipeline
- **Severity Recalculation** - Keyword-based severity assessment independent of source
- **Event Classification** - Automated categorization (database, network, security, etc.)
- **Response Recommendations** - Context-aware operational guidance
- **Human-Readable Summaries** - Formatted output for operational teams

### 🔧 Core Components
- **Signal Server** - MCP-compliant server with proper tool registration
- **Signal Agent** - MCP client with demo workflow capabilities  
- **Main Orchestrator** - Multi-mode deployment coordination
- **Input Validation** - Pydantic schemas for robust data handling

### 🛠️ Development Features
- **MCP Inspector Integration** - Interactive tool testing and debugging
- **Multiple Deployment Modes** - Demo, server-only, and agent-only modes
- **Comprehensive Logging** - Debug-friendly output and error tracking
- **Modern Packaging** - pyproject.toml and professional project structure

### 📊 Supported Event Types
- Database connection issues
- Network connectivity problems
- Resource constraint events
- Security incidents
- Service availability failures

### 🎯 Use Cases
- **Enterprise Operations** - Incident response automation
- **Development Workflows** - CI/CD failure analysis
- **Learning Platform** - MCP protocol reference implementation
- **Research Foundation** - AI-driven operational intelligence

### 🔗 Transport Support
- **stdio Transport** - Development, testing, and MCP Inspector compatibility
- **Future-Ready** - Architecture prepared for HTTP transport evolution

### 📋 Technical Specifications
- Python 3.8+ compatibility
- Official MCP SDK integration
- Pydantic v2 data validation
- Type-safe implementation with comprehensive hints
- Async/await patterns throughout

---

## Version Numbering

Signal Agent follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions  
- **PATCH** version for backwards-compatible bug fixes

### Upcoming Versions

**v1.2.0** - Enhanced Monitoring Integration
- Multiple monitoring tool connectors (Sentry, Datadog, Raygun)
- Advanced pattern recognition
- Historical trend analysis

**v2.0.0** - TriAgent Evolution  
- Production MSP deployment features
- Advanced AI-driven analysis
- Enterprise-grade scalability
- Multi-tenant architecture

---

## Contributing

When contributing to Signal Agent, please:

1. **Follow semantic versioning** principles for changes
2. **Update this changelog** with your modifications
3. **Include migration notes** for breaking changes
4. **Document new features** thoroughly in README
5. **Add appropriate tests** for new functionality

## Links

- [Repository](https://github.com/no0ktheali3n/signals-agent)
- [Issues](https://github.com/no0ktheali3n/signals-agent/issues)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)