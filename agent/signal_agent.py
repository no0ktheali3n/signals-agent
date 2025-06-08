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
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, ValidationError, Field

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

# Configure module logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# INPUT VALIDATION SCHEMA
# =============================================================================

class FailureEventInput(BaseModel):
    """
    Pydantic model for validating incoming failure event data.
    
    This ensures only properly formatted events are processed by the agent,
    providing security against malformed or malicious input.
    """
    event_id: str = Field(..., min_length=1, max_length=100, description="Unique event identifier")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    service: str = Field(..., min_length=1, max_length=200, description="Service or system name")
    severity: Literal["critical", "warning", "info"] = Field(..., description="Event severity level")
    message: str = Field(..., min_length=1, max_length=1000, description="Human-readable failure description")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional structured metadata")

    class Config:
        """Pydantic configuration for strict validation."""
        extra = "forbid"  # Reject any extra fields not in schema
        str_strip_whitespace = True  # Auto-strip whitespace from strings

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
        
    def validate_event_input(self, raw_input: str) -> Optional[Dict[str, Any]]:
        """
        Validate incoming JSON input against the failure event schema.
        
        Args:
            raw_input: Raw JSON string input
            
        Returns:
            Validated event data dict or None if validation fails
        """
        try:
            # Parse JSON
            try:
                raw_data = json.loads(raw_input)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON input: {str(e)}")
                print(f"❌ JSON parsing failed: {str(e)}")
                return None
            
            # Validate against schema
            try:
                validated_event = FailureEventInput(**raw_data)
                logger.info(f"✅ Event validation passed: {validated_event.event_id}")
                return validated_event.dict()
            except ValidationError as e:
                logger.error(f"❌ Schema validation failed: {str(e)}")
                print(f"❌ Input validation failed:")
                for error in e.errors():
                    field = " -> ".join(str(x) for x in error['loc'])
                    print(f"   • {field}: {error['msg']}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Unexpected validation error: {str(e)}")
            print(f"❌ Validation error: {str(e)}")
            return None

    def display_schema_help(self):
        """Display the expected JSON schema format for user reference."""
        print("\n" + "="*60)
        print("EXPECTED JSON INPUT SCHEMA")
        print("="*60)
        print("Required fields:")
        print("• event_id (string, 1-100 chars): Unique identifier")
        print("• timestamp (string): ISO 8601 format (e.g., '2025-06-08T10:30:00Z')")
        print("• service (string, 1-200 chars): Service/system name")
        print("• severity (string): Must be 'critical', 'warning', or 'info'")
        print("• message (string, 1-1000 chars): Failure description")
        print("• details (object, optional): Additional metadata")
        print("\nExample:")
        print(json.dumps({
            "event_id": "sig_001_example",
            "timestamp": "2025-06-08T10:30:00Z",
            "service": "api-gateway",
            "severity": "critical",
            "message": "Service timeout - unable to process requests",
            "details": {
                "error_code": "TIMEOUT",
                "affected_users": 25
            }
        }, indent=2))
        print("="*60 + "\n")

    async def listen_for_events(self):
        """
        Interactive listener mode for processing external failure event inputs.
        
        Continuously accepts JSON input, validates it, and processes through
        the Signal Server for automated failure analysis and response generation.
        """
        logger.info("🎧 Starting Event Listener Mode")
        print("\n" + "="*60)
        print("EVENT LISTENER - AUTONOMOUS PROCESSING MODE")
        print("="*60)
        print("📋 Paste JSON failure event data below")
        print("💡 Type 'help' to see schema requirements")
        print("📝 Multi-line JSON supported - end with empty line")
        print("❌ Type 'exit' to return to main menu")
        print("="*60)
        
        while True:
            try:
                print("\n📥 Waiting for failure event JSON input:")
                print(">>> (paste JSON, press Enter twice when done)")
                
                # Collect multi-line input
                lines = []
                while True:
                    try:
                        line = input()
                        if line.strip() == "":
                            # Empty line signals end of input
                            break
                        lines.append(line)
                    except EOFError:
                        # Handle Ctrl+D
                        break
                
                user_input = "\n".join(lines).strip()
                
                if user_input.lower() == 'exit':
                    print("👋 Exiting event listener mode...")
                    break
                elif user_input.lower() == 'help':
                    self.display_schema_help()
                    continue
                elif not user_input:
                    print("⚠️ Empty input. Paste JSON data or type 'help' for schema.")
                    continue
                
                # Validate input against schema
                validated_event = self.validate_event_input(user_input)
                if not validated_event:
                    print("❌ Event rejected due to validation errors. Type 'help' for schema.")
                    continue
                
                # Process the validated event
                print(f"\n🔄 Processing validated event: {validated_event['event_id']}")
                result = await self.process_failure_event(validated_event)
                
                # Display processing result
                if result and result.get("status") == "processed":
                    print("✅ Event processed successfully!")
                    print(f"📊 Classification: {result.get('classification', 'unknown')}")
                    print(f"⚠️ Calculated Severity: {result.get('calculated_severity', 'unknown')}")
                    print(f"💡 Recommendation: {result.get('recommendation', 'none')}")
                    
                    # Offer to show full response
                    show_full = input("\n📋 Show full analysis result? (y/N): ").strip().lower()
                    if show_full in ['y', 'yes']:
                        print("\n" + "="*50)
                        print("FULL ANALYSIS RESULT")
                        print("="*50)
                        print(json.dumps(result, indent=2))
                        print("="*50)
                else:
                    print("❌ Event processing failed")
                    if 'error' in result:
                        print(f"Error: {result['error']}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Exiting event listener mode...")
                break
            except Exception as e:
                logger.error(f"❌ Listener error: {str(e)}")
                print(f"❌ An error occurred: {str(e)}")

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

    async def get_server_tools(self) -> List[Dict[str, Any]]:
        """Get and display available tools from the MCP server."""
        logger.info("Fetching available tools from server...")
        
        try:
            if self.transport == "http":
                # Use HTTP streamable client for connection
                async with streamablehttp_client(self.server_url) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as session:
                        return await self._get_tools(session)
            else:
                # Use stdio client for connection
                async with stdio_client(self.server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        return await self._get_tools(session)
                        
        except Exception as e:
            logger.error(f"❌ Failed to fetch tools: {str(e)}")
            return []

    async def _get_tools(self, session: ClientSession) -> List[Dict[str, Any]]:
        """Get tools through MCP session."""
        try:
            # Initialize MCP protocol connection
            await session.initialize()
            
            # List available tools
            tools_result = await session.list_tools()
            
            logger.info(f"DEBUG: Tools result type: {type(tools_result)}")
            logger.info(f"DEBUG: Tools result: {tools_result}")
            
            if tools_result and tools_result.tools:
                tools_list = []
                for tool in tools_result.tools:
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": getattr(tool, 'inputSchema', {})
                    }
                    tools_list.append(tool_info)
                
                # Display tools in a nice format
                self._display_tools(tools_list)
                return tools_list
            else:
                logger.warning("⚠️ No tools returned from server")
                return []
                
        except Exception as e:
            logger.error(f"❌ Tools listing session failed: {str(e)}")
            return []

    def _display_tools(self, tools: List[Dict[str, Any]]):
        """Display available tools in a formatted way."""
        print("\n" + "="*70)
        print("AVAILABLE SIGNAL SERVER TOOLS")
        print("="*70)
        
        for i, tool in enumerate(tools, 1):
            print(f"\n🔧 Tool {i}: {tool['name']}")
            print(f"   Description: {tool['description']}")
            
            # Display input schema if available
            if tool.get('input_schema') and isinstance(tool['input_schema'], dict):
                properties = tool['input_schema'].get('properties', {})
                if properties:
                    print("   Parameters:")
                    for param_name, param_info in properties.items():
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('description', 'No description')
                        required_marker = " (required)" if param_name in tool['input_schema'].get('required', []) else ""
                        print(f"     • {param_name} ({param_type}){required_marker}: {param_desc}")
        
        print("="*70 + "\n")
    
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
        logger.info(f"🚀 Running Signal Agent Demo (MCP SDK - {self.transport} transport)")
        
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

    def show_menu(self):
        """Display the main menu options."""
        print("\n" + "="*50)
        print("SIGNAL AGENT - MCP CLIENT")
        print("="*50)
        print("1️⃣  Run Demo")
        print("2️⃣  Get Server Tools & Descriptions")
        print("3️⃣  Event Listener (Autonomous Mode)")
        print("4️⃣  Exit")
        print("="*50)

    async def run_interactive(self):
        """Run the agent in interactive menu mode."""
        logger.info(f"🚀 Starting Signal Agent Interactive Mode (MCP SDK - {self.transport} transport)")
        
        # First, establish connection
        if not await self.connect():
            logger.error("❌ Cannot establish MCP connection to server")
            print("❌ Failed to connect to server. Please ensure server is running.")
            return

        while True:
            self.show_menu()
            
            try:
                choice = input("\n👉 Select an option (1-4): ").strip()
                
                if choice == "1":
                    print("\n🔄 Running demo...")
                    await self.run_demo()
                    
                elif choice == "2":
                    print("\n🔄 Fetching server tools...")
                    tools = await self.get_server_tools()
                    if not tools:
                        print("❌ No tools found or failed to fetch tools")
                
                elif choice == "3":
                    await self.listen_for_events()
                    
                elif choice == "4":
                    print("\n👋 Exiting Signal Agent...")
                    break
                    
                else:
                    print("❌ Invalid choice. Please select 1, 2, 3, or 4.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Exiting Signal Agent...")
                break
            except Exception as e:
                logger.error(f"❌ Menu error: {str(e)}")
                print(f"❌ An error occurred: {str(e)}")
    
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
    parser.add_argument("--demo", action="store_true",
                      help="Run demo directly without menu")
    parser.add_argument("--listen", action="store_true",
                      help="Start directly in event listener mode")
    
    args = parser.parse_args()
    
    # Create agent
    agent = SignalAgent(transport=args.transport, server_url=args.server_url)
    try:
        if args.demo:
            # Run demo directly (backwards compatibility)
            await agent.run_demo()
        elif args.listen:
            # Start directly in listener mode
            if await agent.connect():
                await agent.listen_for_events()
            else:
                print("❌ Failed to connect to server")
        else:
            # Run interactive menu
            await agent.run_interactive()
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())