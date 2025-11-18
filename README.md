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
- **Transport-agnostic design** (stdio for development, HTTP streamable for production)

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

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- [uv](https://docs.astral.sh/uv/) (modern Python package manager)
- [just](https://github.com/casey/just)

### Installation
```bash
git clone https://github.com/no0ktheali3n/signal-agent.git
cd signal-agent

# Setup environment and dependencies
uv venv                         #first time only

just venv                       #activates venv

just init-install               #qol scripts and copes justfile to root

just sync                       #syncs environment dependencies
```

### Run the Demo
```bash
# Full integrated demonstration
just run

# Server only (for MCP Inspector testing)  
just run server

# Agent only (launches server subprocess)
just run agent
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
  "event_id": "string",
  "timestamp": "string", 
  "service": "string",
  "severity": "string",
  "message": "string",
  "details": "object (optional)"
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

or

just run-inspector
```

### Testing HTTP Transport

```bash
# Terminal 1: Start HTTP server
just run-server-http

# Terminal 2: Test with HTTP agent
just run-agent-http

# Or test with direct commands
python main.py server --transport http
python main.py agent --transport http
```

The inspector will provide a web interface at `http://localhost:####` for interactive tool testing.

## 📊 Analysis Pipeline

Signal Agent processes events through a sophisticated multi-stage pipeline:

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
# Test server with MCP Inspector (stdio)
just run-inspector

# Test HTTP server and agent
just run-server-http &    # Background streamable-HTTP MCP server
just run-agent-http       # streamable-HTTP agent test / listener 
```
Our agent serves a two-fold purpose, as an HTTP listener for manual testing and an MCP client to interact with MCP server.

To test manually, run agent and then select option 3 to start listener.

Server runs on localhost:8000, listener runs on localhost:8001.

To test manually (main orchestrator broken with latest update), run chaos_agent:

```bash
#runs chaos agent to run 10 events with 1.5 second delay between event
python agent/chaos_agent.py --count 10 --delay 1.5
```
Events are stored locally in signals_events.db via SQLite.

Now lets run another agent:
```bash
just run-agent-http
```

Now we can use agent as an MCP client to interact with our MCP server and consume tools from server. That allows us to query our signal_events.db to return data about events in a command line interface.

### Code Quality
- **Type hints** throughout codebase
- **Comprehensive logging** for debugging
- **Error handling** with graceful degradation
- **Documentation** for all public interfaces

## 🚀 Evolution Roadmap

Signal Agent represents the foundation for more sophisticated incident response systems:

### 🎯 **Current State (v1.1.0)**
- ✅ Standards-compliant MCP implementation
- ✅ Intelligent event analysis
- ✅ **Dual transport support** (stdio + HTTP streamable)
- ✅ Production-ready architecture
- ✅ **Modern development workflow** with justfile automation

### 🔮 **Future Evolution** 
- 🌐 **HTTP transport** for distributed deployments
- 📊 **Multiple monitoring integrations** (Sentry, Datadog, Raygun)
- 🤖 **Machine learning** enhancement for pattern recognition
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

## 🙏 Acknowledgments

Built with the official Model Context Protocol SDK and inspired by the need for intelligent automation in modern operations.

---

**Signal Agent** - Transforming raw failure events into actionable intelligence through the power of MCP. 🚨➡️🧠