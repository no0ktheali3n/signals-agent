# Signal Agent 🚨

**Intelligent Failure Event Processing via Model Context Protocol (MCP)**

A production-ready MCP server and client system that transforms raw failure events into actionable intelligence through automated classification, severity analysis, and response recommendations.

[![MCP Protocol](https://img.shields.io/badge/MCP-Official%20SDK-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green)](https://python.org)
[![Transport](https://img.shields.io/badge/Transport-stdio%20%7C%20HTTP-orange)](https://modelcontextprotocol.io)

## 🎯 What is Signal Agent?

Signal Agent demonstrates the power of the Model Context Protocol (MCP) for building intelligent automation systems. It processes failure events through a sophisticated analysis pipeline that:

- **🔍 Analyzes** failure event content using keyword-based severity assessment
- **📊 Classifies** events into operational categories (database, network, security, etc.)
- **💡 Generates** appropriate response recommendations
- **📋 Formats** human-readable summaries for operational teams

## ✨ Key Features

### 🏗️ **Production-Ready Architecture**
- **Standards-compliant MCP implementation** using official SDK
- **Robust input validation** with Pydantic schemas
- **Comprehensive error handling** and logging
- **Transport-agnostic design** (stdio for development, HTTP for production)

### 🧠 **Intelligent Analysis Pipeline**
- **Multi-stage event processing** with validation and enrichment
- **Keyword-based severity recalculation** independent of source assessment
- **Operational classification** for proper incident routing
- **Contextual recommendations** based on severity and event type

### 🔧 **Developer Experience**
- **Multiple deployment modes** (integrated demo, server-only, agent-only)
- **MCP Inspector compatibility** for interactive testing
- **Comprehensive logging** and debugging support
- **Clear separation of concerns** between transport and business logic

## Component Architecture

```
┌─────────────────┐    MCP Protocol    ┌──────────────────┐
│   Signal Agent  │◄──────────────────►│  Signal Server   │
│   (Client)      │     stdio/HTTP     │   (MCP Server)   │
│                 │                    │                  │
│ • Event Loading │                    │ • Tool Registry  │
│ • Result Display│                    │ • Event Analysis │
│ • Demo Workflow │                    │ • Classification │
└─────────────────┘                    └──────────────────┘
```

## Transport Evolution

### Development (Current)
- **Transport**: stdio
- **Use Case**: Local development, testing, MCP Inspector integration
- **Benefits**: Simple, reliable, no network dependencies

### Production (Future)
- **Transport**: HTTP (streamable-http)
- **Use Case**: Distributed systems, enterprise deployment
- **Benefits**: Network scalability, multiple clients, load balancing

## Analysis Pipeline

1. **Input Validation** → Pydantic schema enforcement
2. **Severity Analysis** → Keyword-based recalculation  
3. **Event Classification** → Operational categorization
4. **Recommendation** → Context-aware response generation
5. **Formatting** → Human-readable summary creation

## Extensibility Points

- **Analysis Functions**: Easy to add new classification patterns
- **Transport Layer**: Pluggable transport implementations
- **Tool Registry**: Simple addition of new MCP tools
- **Response Formatting**: Customizable output formats

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (modern Python package manager)
- [just](https://github.com/casey/just)

### Installation
```bash
git clone https://github.com/no0ktheali3n/signal-agent.git
cd signal-agent
uv venv
.venv/Scripts/activate
just compile
just sync
```

### Run the Demo
```bash
# Full integrated demonstration
just run

# Server only (for MCP Inspector testing)  
just run-server

# Agent only (launches server subprocess)
just run-agent
```

### Available Commands
```bash
just compile      # Lock dependencies
just sync         # Install dependencies  
just upgrade      # Upgrade all dependencies
just activate     # Activate virtual environment
just run [mode]   # Run Signal Agent (demo/server/agent)
```

## 🏗️ Architecture

Signal Agent follows a clean, modular architecture that separates concerns and enables easy evolution:

```
┌─────────────────┐    MCP Protocol    ┌──────────────────┐
│   Signal Agent  │◄──────────────────►│  Signal Server   │
│   (Client)      │     stdio/HTTP     │   (MCP Server)   │
│                 │                    │                  │
│ • Event Loading │                    │ • Tool Registry  │
│ • Result Display│                    │ • Event Analysis │
│ • Demo Workflow │                    │ • Classification │
└─────────────────┘                    └──────────────────┘
```

### Core Components

#### 🖥️ **Signal Server** (`server/server.py`)
- **MCP-compliant server** using official SDK
- **Tool registration** with proper input schemas
- **Event analysis pipeline** with multi-stage processing
- **Standards-based responses** with TextContent formatting

#### 🤖 **Signal Agent** (`agent/signal_agent.py`)
- **MCP client** with stdio transport
- **Event processing workflow** coordination
- **Result formatting** and display
- **Demo capabilities** with test data

#### 🎛️ **Main Orchestrator** (`main.py`)
- **Multi-mode deployment** (demo, server-only, agent-only)
- **Component lifecycle** management
- **Graceful shutdown** handling

## 🔧 MCP Integration

### Server Tools

#### `classify_failure_event`
Processes failure events through intelligent analysis pipeline.

**Input Schema:**
```json
{
  "event_data": "JSON string containing FailureEvent"
}
```

**Example Usage:**
```json
{
  "event_id": "sig_001_db_failure",
  "timestamp": "2024-12-11T14:30:45Z",
  "service": "user-authentication-service",
  "severity": "critical",
  "message": "PostgreSQL connection pool exhausted",
  "details": {
    "pool_size": 20,
    "active_connections": 20,
    "queue_length": 150
  }
}
```

**Response:**
```json
{
  "event_id": "sig_001_db_failure",
  "original_severity": "critical",
  "calculated_severity": "critical",
  "classification": "database_issue",
  "recommendation": "Immediate attention required - escalate to on-call engineer",
  "human_readable": "🚨 Signal Alert: sig_001_db_failure...",
  "status": "processed"
}
```

#### `health_check`
Server health and connectivity verification.

### Testing with MCP Inspector

```bash

# In another terminal, launch MCP Inspector
npx @modelcontextprotocol/inspector uv run python server/server.py
```

The inspector will provide a web interface at `http://localhost:####` for interactive tool testing.

## 📊 Analysis Pipeline

Signal Agent processes events through multi-stage pipeline:

### 1. **Input Validation**
- JSON parsing and structure validation
- Pydantic model enforcement
- Required field verification

### 2. **Severity Analysis** 
- Keyword-based content analysis
- Pattern matching against severity indicators
- Independent recalculation from source assessment

### 3. **Event Classification**
- Operational category determination
- Pattern matching for:
  - Database issues
  - Network problems  
  - Resource constraints
  - Security incidents
  - Service failures

### 4. **Recommendation Generation**
- Context-aware response suggestions
- Severity-based escalation rules
- Standardized operational procedures

### 5. **Summary Formatting**
- Human-readable result compilation
- Structured display formatting
- Operational dashboard compatibility

## 🎯 Use Cases

### 🏢 **Enterprise Operations**
- **Incident Response Automation** - Intelligent event triage and routing
- **Operational Intelligence** - Pattern recognition and trend analysis  
- **Team Coordination** - Standardized communication and escalation

### 🔧 **Development Workflows**
- **Monitoring Integration** - Process alerts from Sentry, Datadog, etc.
- **CI/CD Enhancement** - Automated failure analysis and reporting
- **Quality Assurance** - Systematic error categorization and tracking

### 📚 **Learning and Research**
- **MCP Protocol Examples** - Reference implementation patterns
- **AI Integration Patterns** - Intelligent automation architectures
- **Protocol Standards** - Best practices for MCP server development

## 🛠️ Development

### Project Structure
```
signal-agent/
├── server/
│   └── server.py          # MCP server implementation
├── agent/
│   └── signal_agent.py    # MCP client implementation
├── main.py                # System orchestrator
├── events/
│   └── test_payload.json  # Demo event data
├── docs/                  # Documentation
└── examples/              # Usage examples
```

### Running Tests
```bash
# Test server with MCP Inspector
just run server
npx @modelcontextprotocol/inspector uv run python server/server.py

# Test full demo
just run

# Test individual components (without just)
uv run python server/server.py        # Server only
uv run python agent/signal_agent.py   # Agent only

# Test individual components (with just)

just run-server
just run-agent
```

### Code Quality
- **Type hints** throughout codebase
- **Comprehensive logging** for debugging
- **Error handling** with graceful degradation
- **Documentation** for all public interfaces

## 🚀 Evolution Roadmap

Signal Agent represents the foundation for more sophisticated incident response systems:

### 🎯 **Current State**
- ✅ Standards-compliant MCP implementation
- ✅ Intelligent event analysis
- ✅ stdio support, integrating https-streamable asap
- ✅ Production-ready architecture

### 🔮 **Future Evolution** 
- 🌐 **HTTP transport** for distributed deployments
- 📊 **Multiple monitoring integrations** (Sentry, Datadog, Raygun)
- 🤖 **Machine learning** enhancement for pattern recognition
- 🤖 **Automated task processes** AI enhanced data interpretation/delivery
- 🤖 **Agentic Augmentations** for contextually aware interactions
- 🏢 **Enterprise features** for MSP environments

## 🤝 Contributing

Contributions are welcome! This project demonstrates MCP best practices and serves as a reference for the community.

### Areas for Contribution
- **Additional analysis patterns** for different event types
- **Transport implementations** (SSE, WebSocket)
- **Integration examples** with popular monitoring tools
- **Documentation improvements** and tutorials

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [Model Context Protocol](https://modelcontextprotocol.io) - Official MCP documentation
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Official Python implementation
- [Demo Video](https://loom.com/your-demo-link) - Live system demonstration

## 🙏 Acknowledgments

Built with the official Model Context Protocol SDK and inspired by the need for intelligent automation in modern operations.

---

**Signal Agent** - Transforming raw failure events into actionable intelligence through the power of MCP. 🚨➡️🧠