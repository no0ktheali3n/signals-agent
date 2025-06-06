# agent/signal_agent.py
"""
Signal Agent - Dual Transport MCP Client for Signal Server Communication

This module implements an MCP client that supports both stdio and HTTP streamable
transports to connect to the Signal Server for failure event processing and 
analysis results display.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

# Configure module logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalAgent:
    """
    Dual transport MCP SDK client for processing failure events through Signal Server.
    """
    
    def __init__(self, 
                 server_command: str = "python", 
                 server_args: Optional[List[str]] = None, 
                 transport: str = "stdio",
                 server_url: str = "http://localhost:8000/mcp"):
        """Initialize Signal Agent with MCP server connection parameters."""
        if server_args is None:
            server_args = ["server/server.py"]
        
        self.transport = transport
        self.server_url = server_url
        
        # Create stdio server parameters (always available)
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args + (["--transport", "http"] if transport == "http" else [])
        )
            
        self.connected = False
        self.server_process = None
        
    async def connect(self) -> bool:
        """Establish connection with Signal Server and perform handshake."""
        try:
            logger.info(f"Connecting to Signal Server via MCP {self.transport} protocol...")
            
            if self.transport == "http":
                # Use HTTP streamable client for connection
                async with streamablehttp_client(self.server_url) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        return await self._initialize_session(session)
            else:
                # Use stdio client for connection
                async with stdio_client(self.server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        return await self._initialize_session(session)
                
        except Exception as e:
            self.connected = False
            logger.error(f"❌ MCP connection failed: {str(e)}")
            logger.error(f"❌ Transport: {self.transport}")
            if self.transport == "http":
                logger.error(f"❌ Server URL: {self.server_url}")
            return False
            
    async def _initialize_session(self, session: ClientSession) -> bool:
        """Initialize MCP session and verify server health."""
        try:
            # Initialize MCP protocol connection
            await session.initialize()
            
            # Verify connectivity by calling health_check tool
            result = await session.call_tool("health_check", {})
            
            logger.info(f"DEBUG: Health check result type: {type(result)}")
            logger.info(f"DEBUG: Health check result: {result}")
            
            if result and result.content:
                # Extract text content from MCP response
                response_text = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        response_text += content.text
                    elif hasattr(content, 'data'):
                        response_text += str(content.data)
                    else:
                        response_text += str(content)
                
                logger.info(f"DEBUG: Raw response content: {repr(response_text)}")
                
                # Parse JSON response for health status
                try:
                    if response_text.strip():
                        health_data = json.loads(response_text)
                        if isinstance(health_data, dict) and health_data.get("status") == "healthy":
                            self.connected = True
                            logger.info("✅ MCP connection established with Signal Server")
                            logger.info(f"Server: {health_data.get('message', 'Unknown')}")
                            logger.info(f"Transport: {health_data.get('transport', self.transport)}")
                            return True
                    else:
                        logger.warning("⚠️ Empty response from health_check")
                        if result and not hasattr(result, 'isError'):
                            self.connected = True
                            logger.info("✅ MCP connection established (empty but successful response)")
                            return True
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"JSON parsing error: {e}")
                    if "healthy" in response_text.lower():
                        self.connected = True
                        logger.info("✅ MCP connection established with Signal Server")
                        return True
            
            self.connected = False
            logger.error("❌ Server handshake failed - unhealthy response")
            return False
            
        except Exception as e:
            self.connected = False
            logger.error(f"❌ Session initialization failed: {str(e)}")
            return False
    
    async def process_failure_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process failure event through Signal Server analysis pipeline."""
        event_id = event_data.get('event_id', 'unknown')
        logger.info(f"Processing failure event via MCP: {event_id}")
        
        try:
            if self.transport == "http":
                # Use HTTP streamable client for connection
                async with streamablehttp_client(self.server_url) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        return await self._process_event(session, event_data)
            else:
                # Use stdio client for connection
                async with stdio_client(self.server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        return await self._process_event(session, event_data)
                        
        except Exception as e:
            logger.error(f"❌ Event processing failed: {str(e)}")
            return {
                "error": str(e),
                "status": "failed",
                "event_id": event_id
            }
            
    async def _process_event(self, session: ClientSession, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process event through MCP session."""
        try:
            # Initialize MCP protocol connection
            await session.initialize()
            
            # **FIXED**: Send individual parameters instead of event_data JSON string
            # Extract event fields for direct parameter passing
            tool_args = {
                "event_id": event_data.get("event_id"),
                "timestamp": event_data.get("timestamp"),
                "service": event_data.get("service"),
                "severity": event_data.get("severity"),
                "message": event_data.get("message"),
                "details": event_data.get("details", {})
            }
            
            logger.info(f"DEBUG: Calling tool with individual parameters: {tool_args}")
            
            # Call MCP tool using individual parameters (not JSON string)
            result = await session.call_tool("classify_failure_event", tool_args)
            
            logger.info(f"DEBUG: Tool call result type: {type(result)}")
            logger.info(f"DEBUG: Tool call result: {result}")
            
            # Process MCP protocol response
            if result and result.content:
                # Extract text content from MCP response
                response_text = ""
                for content in result.content:
                    if hasattr(content, 'text'):
                        response_text += content.text
                    elif hasattr(content, 'data'):
                        response_text += str(content.data)
                    else:
                        response_text += str(content)
                
                logger.info(f"DEBUG: Processing response: {repr(response_text)}")
                
                # Parse JSON response
                try:
                    if response_text.strip():
                        analysis_result = json.loads(response_text)
                        
                        if isinstance(analysis_result, dict) and analysis_result.get("status") == "processed":
                            logger.info("✅ Event analysis completed via MCP protocol")
                            
                            # Display human-readable summary if available
                            if "human_readable" in analysis_result:
                                self._display_analysis_result(analysis_result["human_readable"])
                            
                            return analysis_result
                        else:
                            logger.error("❌ Event analysis failed - invalid response format")
                            return {"error": "Invalid response format", "status": "failed"}
                    else:
                        logger.error("❌ Empty response from server")
                        return {"error": "Empty response content", "status": "failed"}
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Failed to parse JSON response: {str(e)}")
                    logger.error(f"Raw response: {repr(response_text)}")
                    return {
                        "error": f"JSON parsing failed: {str(e)}",
                        "raw_response": response_text,
                        "status": "failed"
                    }
            
            return {
                "error": "Empty response from server",
                "status": "failed"
            }
            
        except Exception as e:
            logger.error(f"❌ Event processing session failed: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }
    
    def _display_analysis_result(self, summary: str):
        """Display formatted analysis result for human consumption."""
        print("\n" + "="*60)
        print("SIGNAL ANALYSIS RESULT")
        print("="*60)
        print(summary)
        print("="*60 + "\n")
    
    async def load_test_event(self, file_path: str = "events/test_payload.json") -> Dict[str, Any]:
        """Load test failure event from JSON file."""
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
        """Execute complete Signal Agent demonstration workflow."""
        logger.info(f"🚀 Starting Signal Agent Demo (MCP SDK - {self.transport} transport)")
        
        # Step 1: Connect to server via selected transport
        if not await self.connect():
            logger.error("Demo failed - cannot establish MCP connection to server")
            return
        
        # Step 2: Use the test event from the logs
        test_event = {
            "event_id": "sig_001_db_failure",
            "timestamp": "2025-05-29T14:30:45Z",
            "service": "user-authentication-service",
            "severity": "critical",
            "message": "PostgreSQL connection pool exhausted - unable to serve authentication requests",
            "details": {
                "database": "auth_db",
                "connection_pool_size": 10,
                "active_connections": 10,
                "queue_length": 47,
                "error_code": "POOL_EXHAUSTED",
                "last_successful_connection": "2025-05-29T14:28:12Z",
                "affected_endpoints": ["/api/v1/login", "/api/v1/refresh", "/api/v1/validate"],
                "estimated_affected_users": 150
            }
        }
        
        logger.info("Using test event from previous logs")
        
        # Step 3: Process event through server via MCP protocol
        result = await self.process_failure_event(test_event)
        
        # Step 4: Report demo status
        if result and result.get("status") == "processed":
            logger.info("🎉 MCP demo completed successfully")
        else:
            logger.error("❌ MCP demo failed during event processing")
    
    async def close(self):
        """Clean up agent resources and close connections."""
        self.connected = False
        logger.info("Signal Agent resources cleaned up")

async def main():
    """Main entry point for standalone agent execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Agent - Dual Transport MCP Client")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                      help="Transport mode (stdio or http)")
    parser.add_argument("--server-url", default="http://localhost:8000/mcp",
                      help="Server URL for HTTP transport")
    
    args = parser.parse_args()
    
    # Create and run agent
    agent = SignalAgent(transport=args.transport, server_url=args.server_url)
    try:
        await agent.run_demo()
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())