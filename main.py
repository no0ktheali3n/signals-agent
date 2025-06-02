# main.py
"""
Signal System Main Orchestrator

This module provides the main entry point and orchestration for the complete
Signal System, coordinating the FastMCP server and Signal Agent for failure
event processing and analysis.

The orchestrator supports multiple deployment modes:
- Full Demo: Integrated server and agent demonstration
- Server Only: Standalone MCP server for external clients
- Agent Only: Standalone client connecting to existing server

Transport: Currently stdio, will implement streamable-http for production deployment
Architecture: Microservice pattern with clear separation of concerns
"""

import asyncio
import logging
import sys

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
    - Concurrent server and agent execution
    - Coordinated startup timing and synchronization
    - Integrated demonstration workflow
    - Graceful shutdown and resource cleanup
    - Error handling and recovery
    """
    
    def __init__(self):
        """Initialize orchestrator with server and agent instances."""
        self.server = SignalServer()
        self.agent = SignalAgent()
        self.running = False
        
    # =========================================================================
    # COMPONENT MANAGEMENT
    # =========================================================================
        
    async def _start_server_background(self):
        """
        Start Signal Server in background mode with streamable-http transport.
        
        Launches MCP server as background task to handle incoming
        client connections while allowing concurrent agent operation.
        
        Server Configuration:
        - Transport: stdio
        - Mode: Continuous operation until shutdown
        - Clients: Supports multiple concurrent connections
        """
        logger.info("🔧 Starting Signal Server (background mode)")
        try:
            # Note: server.start_server() is synchronous, so we run it in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.server.start_server, "stdio")
        except Exception as e:
            logger.error(f"Server startup failed: {str(e)}")
    
    async def _run_agent_demo(self):
        """
        Execute Signal Agent demonstration workflow.
        
        Runs agent demo after appropriate startup delay to ensure
        server availability for connection and processing.
        
        Demo Process:
        - Wait for server startup completion
        - Connect agent to server via streamable-http transport
        - Execute failure event processing demonstration
        - Display analysis results
        """
        # Allow time for server startup and initialization
        await asyncio.sleep(3)
        
        logger.info("🤖 Starting Signal Agent Demo")
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
            logger.info("🚀 Signal System Starting...")
            
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

async def run_server_only():
    """
    Run Signal Server in standalone mode for external client connections.
    
    Starts MCP server with stdio transport for development deployment
    where external agents connect from separate processes or systems.
    
    Use Cases:
    - Development server deployment, production with streamable-http
    - Development with external MCP clients
    - Multi-agent architectures
    - Service-oriented deployments
    
    Server Features:
    - HTTP-based MCP endpoint at /mcp
    - Concurrent client connection support
    - Stateless request/response processing
    - Health monitoring and diagnostics
    """
    logger.info("🔧 Starting Signal Server (standalone mode)")
    logger.info("Server will accept MCP connections via streamable-http transport")
    
    server = SignalServer()

    # run fastmcp in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, server.start_server, "stdio")

async def run_agent_only():
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
    - Network connectivity to server endpoint
    - Compatible MCP protocol versions
    """
    logger.info("🤖 Starting Signal Agent (standalone mode)")
    logger.info("Connecting to existing Signal Server")
    
    agent = SignalAgent()
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
    
    Usage Modes:
    - python main.py          : Full integrated demo
    - python main.py demo     : Explicit full demo mode
    - python main.py server   : Server-only mode
    - python main.py agent    : Agent-only mode
    
    Mode Selection:
    Analyzes command-line arguments to determine appropriate
    deployment configuration and component startup.
    """
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "server":
            # Server-only mode for production deployment
            asyncio.run(run_server_only())
            
        elif mode == "agent":
            # Agent-only mode for external server connection
            asyncio.run(run_agent_only())
            
        elif mode == "demo":
            # Explicit demo mode for full system demonstration
            orchestrator = SignalOrchestrator()
            asyncio.run(orchestrator.start())
            
        else:
            # Invalid argument - show usage information
            print("Usage: python main.py [server|agent|demo]")
            print("  server: Run MCP server only (for external clients)")
            print("  agent:  Run agent only (connect to existing server)")
            print("  demo:   Run complete system demonstration")
            
    else:
        # Default mode - full system demonstration
        print("🚨 Starting Signal System - Full Demonstration")
        print("Use 'python main.py server' for server-only mode")
        print("Use 'python main.py agent' for agent-only mode")
        print("="*60)
        
        orchestrator = SignalOrchestrator()
        asyncio.run(orchestrator.start())

# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()