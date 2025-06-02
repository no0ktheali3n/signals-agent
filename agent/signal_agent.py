# agent/signal_agent.py
"""
Signal Agent - Official MCP SDK Client for Signal Server Communication

This module implements an MCP client using the official MCP SDK that connects 
to the Signal Server via stdio transport to process failure events 
and display analysis results.

The agent provides:
- Official MCP protocol client connection and handshake
- Stdio transport for reliable local process communication
- Failure event processing workflow coordination
- Result formatting and display for human operators
- Demo functionality for testing and validation

Transport: Uses official MCP SDK ClientSession with stdio transport
Architecture: Standards-compliant MCP client with proper protocol implementation

Note: For TriAgent production deployment, this will be upgraded to use
FastMCP with streamable-http transport for network connectivity.
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

# Configure module logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CLIENT IMPLEMENTATION
# =============================================================================

class SignalAgent:
    """
    Official MCP SDK client for processing failure events through Signal Server.
    
    Provides high-level interface for failure event analysis by coordinating
    communication with the Signal Server via official MCP protocol implementation.
    
    Features:
    - Standards-compliant MCP protocol communication
    - Stdio transport for local process connectivity
    - Proper connection lifecycle management
    - Error handling and protocol compliance
    - Human-readable result formatting and display
    - Self-contained demo capabilities
    
    Transport Architecture:
    - Current: stdio transport for local development and testing
    - Future (TriAgent): streamable-http for production MSP deployment
    """
    
    def __init__(self, server_command: str = "python", server_args: Optional[List[str]] = None):
        """
        Initialize Signal Agent with MCP server connection parameters.
        
        Sets up official MCP SDK client for proper MCP protocol communication
        over stdio transport. Prepares agent for connection to Signal Server
        instance running as subprocess or separate process.
        
        Args:
            server_command: Command to start server process (default: "python")
            server_args: Arguments for server command (default: ["server/server.py"])
        """
        if server_args is None:
            server_args = ["server/server.py"]
        
        # Create proper StdioServerParameters object
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args
        )
        self.connected = False
        self.server_process = None
        
    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================
        
    async def connect(self) -> bool:
        """
        Establish connection with Signal Server and perform handshake.
        
        Uses official MCP SDK's stdio transport for proper protocol
        negotiation. Launches server as subprocess and establishes
        ClientSession for MCP communication.
        
        Returns:
            True if connection successful, False otherwise
            
        Connection Process:
        1. Launch Signal Server as subprocess via stdio transport
        2. Create MCP ClientSession with stdin/stdout streams
        3. Initialize MCP protocol connection
        4. Verify server health via health_check tool
        5. Set internal connection state
        """
        try:
            logger.info("Connecting to Signal Server via MCP stdio protocol...")
            
            # Use official MCP SDK stdio client to launch server
            async with stdio_client(self.server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize MCP protocol connection
                    await session.initialize()
                    
                    # Verify connectivity by calling health_check tool
                    result = await session.call_tool("health_check", {})
                    
                    if result and result.content:
                        # Extract text content from MCP response
                        response_text = ""
                        for content in result.content:
                            # Handle different MCP content types safely
                            response_text += getattr(content, 'text', str(content))
                        
                        # Parse JSON response for health status
                        try:
                            health_data = json.loads(response_text) if response_text else {}
                            if isinstance(health_data, dict) and health_data.get("status") == "healthy":
                                self.connected = True
                                logger.info("✅ MCP connection established with Signal Server")
                                logger.info(f"Server: {health_data.get('message', 'Unknown')}")
                                logger.info(f"Transport: {health_data.get('transport', 'stdio')}")
                                return True
                        except (json.JSONDecodeError, AttributeError):
                            # Check if response indicates success without JSON parsing
                            if "healthy" in response_text.lower():
                                self.connected = True
                                logger.info("✅ MCP connection established with Signal Server")
                                return True
                
                self.connected = False
                logger.error("❌ Server handshake failed - unhealthy response")
                return False
                
        except Exception as e:
            self.connected = False
            logger.error(f"❌ MCP connection failed: {str(e)}")
            return False
    
    # =========================================================================
    # EVENT PROCESSING WORKFLOW
    # =========================================================================
    
    async def process_failure_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process failure event through Signal Server analysis pipeline.
        
        Uses official MCP SDK ClientSession to invoke server tools with 
        proper MCP protocol compliance. Coordinates complete event analysis 
        workflow including protocol communication, result processing, and 
        human-readable display.
        
        Args:
            event_data: Failure event dictionary with required fields
            
        Returns:
            Server analysis result dictionary
            
        Processing Flow:
        1. Launch Signal Server subprocess via stdio transport
        2. Create ClientSession with stdin/stdout streams
        3. Initialize MCP protocol connection
        4. Prepare event data for MCP tool invocation
        5. Call classify_failure_event tool via MCP protocol
        6. Process MCP response content and extract results
        7. Format and display human-readable summary
        8. Return structured results for further use
        """
        event_id = event_data.get('event_id', 'unknown')
        logger.info(f"Processing failure event via MCP: {event_id}")
        
        try:
            # Use official MCP SDK stdio client for proper protocol communication
            async with stdio_client(self.server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize MCP protocol connection
                    await session.initialize()
                    
                    # Prepare event data as JSON string for MCP tool
                    event_json = json.dumps(event_data)
                    
                    # Call MCP tool using official protocol
                    result = await session.call_tool("classify_failure_event", {"event_data": event_json})
                    
                    # Process MCP protocol response
                    if result and result.content:
                        # Extract text content from MCP response
                        response_text = ""
                        for content in result.content:
                            # Handle different MCP content types safely
                            response_text += getattr(content, 'text', str(content))
                        
                        # Parse JSON result from MCP response
                        try:
                            analysis_result = json.loads(response_text) if response_text else {}
                            
                            if isinstance(analysis_result, dict) and analysis_result.get("status") == "processed":
                                logger.info("✅ Event analysis completed via MCP protocol")
                                
                                # Display human-readable summary if available
                                if "human_readable" in analysis_result:
                                    self._display_analysis_result(analysis_result["human_readable"])
                                
                                return analysis_result
                            else:
                                logger.error("❌ Event analysis failed - invalid response format")
                                return {"error": "Invalid response format", "status": "failed"}
                                
                        except (json.JSONDecodeError, AttributeError) as e:
                            logger.error(f"❌ Failed to parse MCP response: {str(e)}")
                            return {"error": f"Response parsing failed: {str(e)}", "status": "failed"}
                    else:
                        logger.error("❌ Event analysis failed - empty MCP response")
                        return {"error": "Empty response from server", "status": "failed"}
                        
        except Exception as e:
            logger.error(f"❌ MCP event processing failed: {str(e)}")
            return {"error": str(e), "status": "failed"}
    
    def _display_analysis_result(self, summary: str):
        """
        Display formatted analysis result for human consumption.
        
        Creates visually structured output for operational dashboards,
        console interfaces, or notification systems.
        
        Args:
            summary: Human-readable analysis summary from server
        """
        print("\n" + "="*60)
        print("SIGNAL ANALYSIS RESULT")
        print("="*60)
        print(summary)
        print("="*60 + "\n")
    
    # =========================================================================
    # DEMO AND TESTING
    # =========================================================================
    
    async def load_test_event(self, file_path: str = "events/test_payload.json") -> Dict[str, Any]:
        """
        Load test failure event from JSON file.
        
        Provides test data loading for development and demonstration
        purposes. Falls back to default event if file unavailable.
        
        Args:
            file_path: Path to test event JSON file
            
        Returns:
            Test event data dictionary
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Test file not found: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading test event: {str(e)}")
            return {}
    
    async def run_demo(self):
        """
        Execute complete Signal Agent demonstration workflow.
        
        Provides end-to-end demonstration of agent capabilities using
        official MCP SDK for standards-compliant protocol communication.
        
        Demo Flow:
        1. Establish MCP server connection via stdio protocol
        2. Load or create test failure event
        3. Process event through server analysis via MCP tools
        4. Display formatted results
        5. Report final status
        """
        logger.info("🚀 Starting Signal Agent Demo (Official MCP SDK)")
        
        # Step 1: Connect to server via MCP protocol
        if not await self.connect():
            logger.error("Demo failed - cannot establish MCP connection to server")
            return
        
        # Step 2: Load test event data
        test_event = await self.load_test_event()
        if not test_event:
            # Create default test event if file unavailable
            test_event = {
                "event_id": "demo_001",
                "timestamp": datetime.now().isoformat(),
                "service": "demo-authentication-service",
                "severity": "critical",
                "message": "Database connection pool exhausted - authentication requests failing",
                "details": {
                    "connection_pool_size": 10,
                    "active_connections": 10,
                    "queue_length": 25,
                    "affected_users": 150
                }
            }
            logger.info("Using default test event for MCP demo")
        
        # Step 3: Process event through server via MCP protocol
        result = await self.process_failure_event(test_event)
        
        # Step 4: Report demo status
        if result and result.get("status") == "processed":
            logger.info("🎉 MCP demo completed successfully")
        else:
            logger.error("❌ MCP demo failed during event processing")
    
    # =========================================================================
    # RESOURCE MANAGEMENT
    # =========================================================================
    
    async def close(self):
        """
        Clean up agent resources and close connections.
        
        Official MCP SDK handles connection cleanup automatically when
        exiting context managers, but this method provides explicit cleanup
        for scenarios where manual resource management is needed.
        """
        self.connected = False
        logger.info("Signal Agent resources cleaned up")

# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

async def main():
    """
    Main entry point for standalone agent execution.
    
    Creates Signal Agent instance and runs demonstration workflow
    using official MCP SDK for standards-compliant protocol communication.
    """
    agent = SignalAgent()
    try:
        await agent.run_demo()
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())