# main.py
"""
Signal System Main Orchestrator

This module provides the main entry point and orchestration for the complete
Signal System, coordinating the dual-transport MCP server and Signal Agent for failure
event processing and analysis.

The orchestrator supports multiple deployment modes:
- Full Demo: Integrated server and agent demonstration
- Server Only: Standalone MCP server for external clients
- Agent Only: Standalone client connecting to existing server

Transport: Supports both stdio (development) and HTTP streamable (production)
Architecture: Microservice pattern with clear separation of concerns and transport flexibility
"""

import asyncio
import logging
import sys
import argparse

from agent.signal_agent import SignalAgent
from server.server import SignalServer

# Configure system-wide logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM ORCHESTRATOR
# =============================================================================

class SignalOrchestrator:
    """
    Coordinates Signal System components for integrated operation.
    
    Manages lifecycle of both MCP server and client agent, providing
    synchronized startup, demonstration workflow, and graceful shutdown
    for complete system testing and validation.
    
    Features:
    - Concurrent server and agent execution with transport selection
    - Coordinated startup timing and synchronization
    - Integrated demonstration workflow
    - Graceful shutdown and resource cleanup
    - Error handling and recovery
    - Transport-agnostic operation (stdio or HTTP streamable)
    """
    
    def __init__(self, transport: str = "stdio", server_url: str = "http://localhost:8000/mcp"):
        """Initialize orchestrator with server and agent instances."""
        self.server = SignalServer()
        self.agent = SignalAgent(transport=transport, server_url=server_url)
        self.running = False
        self.transport = transport
        self.server_url = server_url
        
    # =========================================================================
    # COMPONENT MANAGEMENT
    # =========================================================================
        
    async def _start_server_background(self):
        """
        Start Signal Server in background mode with selected transport.
        
        Launches MCP server as background task to handle incoming
        client connections while allowing concurrent agent operation.
        
        Server Configuration:
        - Transport: stdio (development) or HTTP streamable (production)
        - Mode: Continuous operation until shutdown
        - Clients: Supports multiple concurrent connections
        """
        logger.info(f"🔧 Starting Signal Server (background mode) with {self.transport} transport")
        try:
            # Import and use the async serve function directly
            from server.server import serve_async
            await serve_async(self.transport)
        except Exception as e:
            logger.error(f"Server startup failed: {str(e)}")
    
    async def _run_agent_demo(self):
        """
        Execute Signal Agent demonstration workflow.
        
        Runs agent demo after appropriate startup delay to ensure
        server availability for connection and processing.
        
        Demo Process:
        - Wait for server startup completion
        - Connect agent to server via selected transport
        - Execute failure event processing demonstration
        - Display analysis results
        """
        # Allow time for server startup and initialization
        if self.transport == "http":
            logger.info("⏳ Waiting for HTTP server startup (5 seconds)...")
            await asyncio.sleep(5)  # HTTP server needs more time
        else:
            logger.info("⏳ Waiting for stdio server startup (2 seconds)...")
            await asyncio.sleep(2)  # stdio server starts faster
        
        logger.info(f"🤖 Starting Signal Agent Demo with {self.transport} transport")
        await self.agent.run_demo()
    
    # =========================================================================
    # SYSTEM LIFECYCLE
    # =========================================================================
    
    async def start(self):
        """
        Start complete Signal System with coordinated server and agent.
        
        Orchestrates system startup with proper component synchronization,
        runs integrated demonstration, and maintains server operation for
        continued use after demo completion.
        
        Startup Flow:
        1. Create concurrent tasks for server and agent
        2. Start server in background for continuous operation
        3. Execute agent demonstration workflow
        4. Maintain server operation for external connections
        5. Handle shutdown signals gracefully
        """
        self.running = True
        server_task = None
        
        try:
            logger.info(f"🚀 Signal System Starting with {self.transport} transport...")
            
            if self.transport == "http":
                logger.info(f"🌐 HTTP Server URL: {self.server_url}")
            
            # Create concurrent tasks for server and agent
            server_task = asyncio.create_task(self._start_server_background())
            agent_task = asyncio.create_task(self._run_agent_demo())
            
            # Wait for agent demo completion
            await agent_task
            
            # Continue server operation for external clients
            logger.info("🔄 Server running - available for external connections")
            logger.info("Press Ctrl+C to shutdown")
            
            # Keep server running until interrupted
            await server_task
            
        except KeyboardInterrupt:
            logger.info("⏹️  Shutdown requested - stopping Signal System")
            # Cancel the background server task to allow clean exit
            if server_task is not None:
                server_task.cancel()
                try:
                    await server_task  # Wait for cancellation to complete
                except asyncio.CancelledError:
                    pass  # Expected when we cancel the task
            self.running = False

        except Exception as e:
            logger.error(f"❌ System error: {str(e)}")
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """
        Clean up system resources and connections.
        
        Ensures proper resource cleanup for both server and agent
        components to prevent resource leaks or hanging processes.
        """
        logger.info("🧹 Cleaning up system resources")
        await self.agent.close()
        self.running = False

# =============================================================================
# STANDALONE COMPONENT RUNNERS
# =============================================================================

async def run_server_only(transport: str = "stdio"):
    """
    Run Signal Server in standalone mode for external client connections.
    
    Starts MCP server with selected transport for development or production deployment
    where external agents connect from separate processes or systems.
    
    Use Cases:
    - Development server with stdio transport (MCP Inspector testing)
    - Production deployment with HTTP streamable transport
    - Multi-agent architectures
    - Service-oriented deployments
    
    Server Features:
    - stdio: Direct process communication, perfect for development
    - http: Network-based communication, ideal for production
    - Concurrent client connection support
    - Health monitoring and diagnostics
    """
    logger.info(f"🔧 Starting Signal Server (standalone mode) with {transport} transport")
    
    if transport == "http":
        logger.info("🌐 HTTP Server will be available at: http://localhost:8000/mcp")
        logger.info("📋 Connect clients to: http://localhost:8000/mcp")
    else:
        logger.info("📋 Server ready for stdio connections (MCP Inspector compatible)")
        logger.info("🔍 Test with: npx @modelcontextprotocol/inspector python server/server.py")
    
    # Import and use the async serve function directly
    from server.server import serve_async
    await serve_async(transport)

async def run_agent_only(transport: str = "stdio", server_url: str = "http://localhost:8000/mcp"):
    """
    Run Signal Agent in standalone mode connecting to existing server.
    
    Starts agent client that connects to external MCP server for
    event processing. Useful for testing agent functionality or
    connecting to remote server instances.
    
    Use Cases:
    - Agent testing with existing server
    - Remote server connections
    - Distributed system architectures
    - Client-only deployments
    
    Prerequisites:
    - Signal Server must be running and accessible
    - For HTTP: Server at specified URL
    - For stdio: Agent will launch server subprocess
    """
    logger.info(f"🤖 Starting Signal Agent (standalone mode) with {transport} transport")
    
    if transport == "http":
        logger.info(f"🌐 Connecting to HTTP server at: {server_url}")
        logger.info("⚠️  Ensure server is running: python main.py server --transport http")
    else:
        logger.info("📋 Agent will launch stdio server subprocess")
    
    agent = SignalAgent(transport=transport, server_url=server_url)
    try:
        await agent.run_demo()
    finally:
        await agent.close()

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def main():
    """
    Main entry point with flexible deployment mode selection.
    
    Provides command-line interface for running Signal System in
    different configurations based on deployment requirements.
    
    Usage Examples:
    - python main.py                              : Full demo (stdio)
    - python main.py --transport http             : Full demo (HTTP)
    - python main.py server                       : Server only (stdio)
    - python main.py server --transport http      : Server only (HTTP)
    - python main.py agent                        : Agent only (stdio)
    - python main.py agent --transport http       : Agent only (HTTP)
    - python main.py demo --transport http        : Explicit demo (HTTP)
    
    Transport Modes:
    - stdio: Development, testing, MCP Inspector compatibility
    - http:  Production, distributed systems, network deployment
    """
    parser = argparse.ArgumentParser(description="Signal System - Dual Transport MCP Server/Agent")
    parser.add_argument("mode", nargs="?", choices=["server", "agent", "demo"], default="demo",
                      help="Operation mode (server, agent, or demo)")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                      help="Transport mode (stdio for development, http for production)")
    parser.add_argument("--server-url", default="http://localhost:8000/mcp",
                      help="Server URL for HTTP transport (default: http://localhost:8000/mcp)")
    
    args = parser.parse_args()
    
    # Display startup banner
    print("🚨 Signal System - Intelligent MCP-based Failure Event Processing")
    print("="*70)
    print(f"Mode: {args.mode}")
    print(f"Transport: {args.transport}")
    if args.transport == "http":
        print(f"Server URL: {args.server_url}")
    print("="*70)
    
    if args.mode == "server":
        # Server-only mode
        print(f"🔧 Server-only mode with {args.transport} transport")
        if args.transport == "http":
            print("🌐 Production HTTP streamable server")
            print("📋 Clients can connect via HTTP to /mcp endpoint")
        else:
            print("📋 Development stdio server")
            print("🔍 Compatible with MCP Inspector and stdio clients")
        print("-" * 70)
        
        asyncio.run(run_server_only(args.transport))
        
    elif args.mode == "agent":
        # Agent-only mode
        print(f"🤖 Agent-only mode with {args.transport} transport")
        if args.transport == "http":
            print("🌐 Connecting to HTTP streamable server")
            print("⚠️  Ensure server is running separately")
        else:
            print("📋 Launching stdio server subprocess")
        print("-" * 70)
        
        asyncio.run(run_agent_only(args.transport, args.server_url))
        
    else:
        # Demo mode (default)
        print(f"🚨 Full System Demo with {args.transport} transport")
        if args.transport == "http":
            print("🌐 Production-like HTTP streamable deployment")
            print("📊 Demonstrates distributed system capabilities")
        else:
            print("📋 Development stdio deployment")
            print("🔍 Perfect for local testing and development")
        print("-" * 70)
        
        orchestrator = SignalOrchestrator(args.transport, args.server_url)
        asyncio.run(orchestrator.start())

# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()