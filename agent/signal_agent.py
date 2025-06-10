# agent/signal_agent.py
"""
Signal Agent - Dual Transport MCP Client for Signal Server Communication

This module implements an MCP client that supports both stdio and HTTP streamable
transports to connect to the Signal Server for failure event processing and 
analysis results display.

Features:
- Dual MCP transport support (stdio/http)
- HTTP listener for external event ingestion
- Input validation and schema enforcement
- Interactive and automated processing modes
"""

import asyncio
import json
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Literal, Union
from pydantic import BaseModel, ValidationError, Field

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# SCHEMA & MODELS
# =============================================================================

class FailureEventInput(BaseModel):
    """Pydantic model for validating incoming failure event data."""
    event_id: str = Field(..., min_length=1, max_length=100)
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    service: str = Field(..., min_length=1, max_length=200)
    severity: Literal["critical", "warning", "info"]
    message: str = Field(..., min_length=1, max_length=1000)
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"
        str_strip_whitespace = True

# =============================================================================
# SIGNAL AGENT
# =============================================================================

class SignalAgent:
    """
    Dual transport MCP client for processing failure events through Signal Server.
    
    Supports both stdio and HTTP streamable transports for MCP communication,
    plus HTTP listener for external event ingestion.
    """
    
    def __init__(self, 
                 server_command: str = "python", 
                 server_args: Optional[List[str]] = None, 
                 transport: str = "stdio",
                 server_url: str = "http://localhost:8000/mcp",
                 listen_port: int = 8001):
        """Initialize Signal Agent with MCP server connection parameters."""
        self.server_args = server_args or ["server/server.py"]
        self.transport = transport
        self.server_url = server_url
        self.listen_port = listen_port
        self.connected = False
        
        # Stdio server parameters
        self.server_params = StdioServerParameters(
            command=server_command,
            args=self.server_args + (["--transport", "http"] if transport == "http" else [])
        )
        
        # HTTP listener state
        self.http_server = None
        self.http_thread = None
        self.listening = False

    # =============================================================================
    # VALIDATION & UTILITIES
    # =============================================================================

    def validate_event(self, event_input: Union[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Unified validation for both string JSON and dict inputs.
        
        Args:
            event_input: Raw JSON string or dictionary
            
        Returns:
            Validated event data dict or None if validation fails
        """
        try:
            # Parse if string input
            if isinstance(event_input, str):
                try:
                    event_data = json.loads(event_input)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON: {str(e)}")
                    print(f"❌ JSON parsing failed: {str(e)}")
                    return None
            else:
                event_data = event_input
            
            # Validate against schema
            validated_event = FailureEventInput(**event_data)
            logger.info(f"✅ Event validation passed: {validated_event.event_id}")
            return validated_event.model_dump()
            
        except ValidationError as e:
            logger.error(f"❌ Schema validation failed: {str(e)}")
            if isinstance(event_input, str):  # Only print for interactive mode
                print("❌ Input validation failed:")
                for error in e.errors():
                    field = " -> ".join(str(x) for x in error['loc'])
                    print(f"   • {field}: {error['msg']}")
            return None
        except Exception as e:
            logger.error(f"❌ Validation error: {str(e)}")
            return None

    def display_schema_help(self):
        """Display the expected JSON schema format."""
        schema_example = {
            "event_id": "sig_001_example",
            "timestamp": "2025-06-08T10:30:00Z",
            "service": "api-gateway",
            "severity": "critical",
            "message": "Service timeout - unable to process requests",
            "details": {"error_code": "TIMEOUT", "affected_users": 25}
        }
        
        print("\n" + "="*60)
        print("EXPECTED JSON INPUT SCHEMA")
        print("="*60)
        print("Required fields:")
        print("• event_id (1-100 chars): Unique identifier")
        print("• timestamp: ISO 8601 format")
        print("• service (1-200 chars): Service/system name") 
        print("• severity: 'critical', 'warning', or 'info'")
        print("• message (1-1000 chars): Failure description")
        print("• details (optional): Additional metadata")
        print(f"\nExample:\n{json.dumps(schema_example, indent=2)}")
        print("="*60 + "\n")

    # =============================================================================
    # HTTP LISTENER
    # =============================================================================

    class EventHandler(BaseHTTPRequestHandler):
        """HTTP request handler for receiving events."""
        
        def __init__(self, signal_agent, *args, **kwargs):
            self.signal_agent = signal_agent
            super().__init__(*args, **kwargs)
        
        def _send_json_response(self, status: int, data: Dict[str, Any]):
            """Helper to send JSON responses."""
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        
        def do_POST(self):
            """Handle POST requests with event data."""
            if self.path != '/events':
                self.send_response(404)
                self.end_headers()
                return
                
            try:
                # Read and parse request
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                event_data = json.loads(body)
                
                # Validate event
                validated_event = self.signal_agent.validate_event(event_data)
                if not validated_event:
                    self._send_json_response(400, {"error": "Event validation failed"})
                    return
                
                # Process event in new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.signal_agent.process_failure_event(validated_event)
                    )
                    
                    if result and result.get("status") == "processed":
                        self._send_json_response(200, {
                            "status": "processed",
                            "event_id": validated_event['event_id'],
                            "classification": result.get('classification'),
                            "calculated_severity": result.get('calculated_severity'),
                            "recommendation": result.get('recommendation')
                        })
                    else:
                        self._send_json_response(500, {"error": "Event processing failed"})
                finally:
                    loop.close()
                    
            except json.JSONDecodeError:
                self._send_json_response(400, {"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"❌ Event processing error: {str(e)}")
                self._send_json_response(500, {"error": str(e)})
        
        def do_GET(self):
            """Handle GET requests for health checks."""
            if self.path == '/health':
                self._send_json_response(200, {
                    "status": "healthy",
                    "service": "signal-agent",
                    "listening": True,
                    "mcp_connected": self.signal_agent.connected
                })
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            """Suppress HTTP server logs."""
            pass

    def start_http_listener(self):
        """Start HTTP listener in background thread."""
        def run_server():
            self.http_server = HTTPServer(
                ('localhost', self.listen_port),
                lambda *args, **kwargs: SignalAgent.EventHandler(self, *args, **kwargs)
            )
            logger.info(f"🌐 HTTP listener started on http://localhost:{self.listen_port}")
            self.listening = True
            self.http_server.serve_forever()
        
        self.http_thread = threading.Thread(target=run_server, daemon=True)
        self.http_thread.start()
        
        # Wait a moment for server to actually start
        import time
        time.sleep(0.5)

    def stop_http_listener(self):
        """Stop HTTP listener."""
        if self.http_server:
            self.http_server.shutdown()
            self.listening = False
            logger.info("🛑 HTTP listener stopped")

    async def listen_for_http_events(self):
        """HTTP event listener mode - starts HTTP server and waits for events."""
        logger.info("🌐 Starting HTTP Event Listener Mode")
        print("\n" + "="*70)
        print("HTTP EVENT LISTENER - EXTERNAL SOURCE MODE")
        print("="*70)
        print("🌐 Starting HTTP server for external event sources...")
        print("📡 External systems can POST events to /events endpoint")
        print("❌ Press Ctrl+C to stop the listener")
        print("="*70)
        
        # Ensure MCP connection
        if not await self.connect():
            print("❌ Failed to connect to Signal Server. Ensure server is running.")
            return
        
        # Start HTTP listener
        self.start_http_listener()
        
        # Now show ready message after server has started
        print(f"\n✅ HTTP listener active on port {self.listen_port}")
        print(f"📡 Send events to: POST http://localhost:{self.listen_port}/events")
        print(f"🔗 Connected to Signal Server via {self.transport} transport")
        print("\n🎧 Waiting for events...")
        
        try:
            while self.listening:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping HTTP event listener...")
        finally:
            self.stop_http_listener()

    # =============================================================================
    # MCP CONNECTION & SESSION MANAGEMENT
    # =============================================================================

    async def connect(self) -> bool:
        """Establish connection with Signal Server and perform handshake."""
        logger.info(f"Connecting to Signal Server via MCP {self.transport} protocol...")
        
        try:
            if self.transport == "http":
                async with streamablehttp_client(self.server_url) as session_context:
                    return await self._initialize_session(session_context)
            else:
                async with stdio_client(self.server_params) as session_context:
                    return await self._initialize_session(session_context)
        except Exception as e:
            self.connected = False
            logger.error(f"❌ MCP connection failed: {str(e)}")
            return False

    async def _initialize_session(self, session_context) -> bool:
        """Initialize MCP session and verify server health."""
        try:
            if self.transport == "http":
                read_stream, write_stream, _ = session_context
            else:
                read_stream, write_stream = session_context
                
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # Health check
                result = await session.call_tool("health_check", {})
                
                if result and result.content:
                    response_text = "".join(
                        content.text if hasattr(content, 'text') else str(content)
                        for content in result.content
                    )
                    
                    # Parse health response
                    if response_text.strip():
                        try:
                            health_data = json.loads(response_text)
                            if health_data.get("status") == "healthy":
                                self.connected = True
                                logger.info("✅ MCP connection established with Signal Server")
                                return True
                        except json.JSONDecodeError:
                            if "healthy" in response_text.lower():
                                self.connected = True
                                logger.info("✅ MCP connection established with Signal Server")
                                return True
                    else:
                        # Empty but successful response
                        if not hasattr(result, 'isError'):
                            self.connected = True
                            logger.info("✅ MCP connection established")
                            return True
                
                logger.error("❌ Server handshake failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Session initialization failed: {str(e)}")
            return False

    async def _execute_with_session(self, operation):
        """Execute operation with appropriate MCP session."""
        try:
            if self.transport == "http":
                async with streamablehttp_client(self.server_url) as session_context:
                    read_stream, write_stream, _ = session_context
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        return await operation(session)
            else:
                async with stdio_client(self.server_params) as session_context:
                    read_stream, write_stream = session_context
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        return await operation(session)
        except Exception as e:
            logger.error(f"❌ Session operation failed: {str(e)}")
            return None

    # =============================================================================
    # CORE PROCESSING
    # =============================================================================

    async def process_failure_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process failure event through Signal Server analysis pipeline."""
        event_id = event_data.get('event_id', 'unknown')
        logger.info(f"Processing failure event via MCP: {event_id}")
        
        async def process_operation(session):
            tool_args = {
                "event_id": event_data.get("event_id"),
                "timestamp": event_data.get("timestamp"),
                "service": event_data.get("service"),
                "severity": event_data.get("severity"),
                "message": event_data.get("message"),
                "details": event_data.get("details", {})
            }
            
            result = await session.call_tool("classify_failure_event", tool_args)
            
            if result and result.content:
                response_text = "".join(
                    content.text if hasattr(content, 'text') else str(content)
                    for content in result.content
                )
                
                if response_text.strip():
                    analysis_result = json.loads(response_text)
                    if analysis_result.get("status") == "processed":
                        logger.info("✅ Event analysis completed via MCP protocol")
                        
                        # Display summary if available
                        if "human_readable" in analysis_result:
                            self._display_analysis_result(analysis_result["human_readable"])
                        
                        return analysis_result
            
            return {"error": "Processing failed", "status": "failed"}
        
        result = await self._execute_with_session(process_operation)
        return result or {"error": "Session error", "status": "failed", "event_id": event_id}

    def _display_analysis_result(self, summary: str):
        """Display formatted analysis result."""
        print(f"\n{'='*60}\nSIGNAL ANALYSIS RESULT\n{'='*60}")
        print(summary)
        print("="*60 + "\n")

    # =============================================================================
    # INTERACTIVE MODES
    # =============================================================================

    async def listen_for_events(self):
        """Interactive listener mode for manual JSON input."""
        logger.info("🎧 Starting Event Listener Mode")
        print(f"\n{'='*60}\nEVENT LISTENER - MANUAL INPUT MODE\n{'='*60}")
        print("📋 Paste JSON failure event data below")
        print("💡 Type 'help' for schema • 'exit' to return")
        print("📝 Multi-line JSON supported - end with empty line")
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
                            break
                        lines.append(line)
                    except EOFError:
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
                
                # Process event
                validated_event = self.validate_event(user_input)
                if not validated_event:
                    print("❌ Event rejected. Type 'help' for schema.")
                    continue
                
                print(f"\n🔄 Processing event: {validated_event['event_id']}")
                result = await self.process_failure_event(validated_event)
                
                if result and result.get("status") == "processed":
                    print("✅ Event processed successfully!")
                    print(f"📊 Classification: {result.get('classification', 'unknown')}")
                    print(f"⚠️ Severity: {result.get('calculated_severity', 'unknown')}")
                    print(f"💡 Recommendation: {result.get('recommendation', 'none')}")
                    
                    if input("\n📋 Show full result? (y/N): ").strip().lower() in ['y', 'yes']:
                        print(f"\n{'='*50}\nFULL ANALYSIS RESULT\n{'='*50}")
                        print(json.dumps(result, indent=2))
                        print("="*50)
                else:
                    print("❌ Event processing failed")
                    if 'error' in result:
                        print(f"Error: {result['error']}")
                
            except KeyboardInterrupt:
                print("\n👋 Exiting event listener mode...")
                break
            except Exception as e:
                logger.error(f"❌ Listener error: {str(e)}")
                print(f"❌ Error: {str(e)}")

    # =============================================================================
    # TOOLS & DEMO
    # =============================================================================

    async def get_server_tools(self) -> List[Dict[str, Any]]:
        """Get and display available tools from the MCP server."""
        logger.info("Fetching available tools from server...")
        
        async def tools_operation(session):
            tools_result = await session.list_tools()
            
            if tools_result and tools_result.tools:
                tools_list = []
                for tool in tools_result.tools:
                    tools_list.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": getattr(tool, 'inputSchema', {})
                    })
                
                self._display_tools(tools_list)
                return tools_list
            
            logger.warning("⚠️ No tools returned from server")
            return []
        
        return await self._execute_with_session(tools_operation) or []

    def _display_tools(self, tools: List[Dict[str, Any]]):
        """Display available tools."""
        print(f"\n{'='*70}\nAVAILABLE SIGNAL SERVER TOOLS\n{'='*70}")
        
        for i, tool in enumerate(tools, 1):
            print(f"\n🔧 Tool {i}: {tool['name']}")
            print(f"   Description: {tool['description']}")
            
            if tool.get('input_schema', {}).get('properties'):
                print("   Parameters:")
                properties = tool['input_schema']['properties']
                required = tool['input_schema'].get('required', [])
                
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'unknown')
                    param_desc = param_info.get('description', 'No description')
                    required_marker = " (required)" if param_name in required else ""
                    print(f"     • {param_name} ({param_type}){required_marker}: {param_desc}")
        
        print("="*70 + "\n")

    async def run_demo(self):
        """Execute demo with test event."""
        logger.info(f"🚀 Running Signal Agent Demo ({self.transport} transport)")
        
        if not await self.connect():
            logger.error("Demo failed - cannot establish MCP connection")
            return
        
        # Test event
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
                "estimated_affected_users": 150
            }
        }
        
        result = await self.process_failure_event(test_event)
        
        if result and result.get("status") == "processed":
            logger.info("🎉 Demo completed successfully")
        else:
            logger.error("❌ Demo failed during event processing")

    # =============================================================================
    # MAIN INTERFACE
    # =============================================================================

    def show_menu(self):
        """Display main menu."""
        print(f"\n{'='*50}\nSIGNAL AGENT - MCP CLIENT\n{'='*50}")
        print("1️⃣  Run Demo")
        print("2️⃣  Get Server Tools & Descriptions") 
        print("3️⃣  Event Listener (Manual Input Test)")
        print("4️⃣  HTTP Event Listener (External Events)")
        print("5️⃣  Exit")
        print("="*50)

    async def run_interactive(self):
        """Run interactive menu mode."""
        logger.info(f"🚀 Starting Signal Agent Interactive Mode ({self.transport} transport)")
        
        if not await self.connect():
            print("❌ Failed to connect to server. Please ensure server is running.")
            return

        while True:
            self.show_menu()
            
            try:
                choice = input("\n👉 Select option (1-5): ").strip()
                
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
                    await self.listen_for_http_events()
                elif choice == "5":
                    print("\n👋 Exiting Signal Agent...")
                    break
                else:
                    print("❌ Invalid choice. Please select 1-5.")
                    
            except KeyboardInterrupt:
                print("\n👋 Exiting Signal Agent...")
                break
            except Exception as e:
                logger.error(f"❌ Menu error: {str(e)}")
                print(f"❌ Error: {str(e)}")

    async def close(self):
        """Clean up resources."""
        self.stop_http_listener()
        self.connected = False
        logger.info("Signal Agent resources cleaned up")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Agent - Dual Transport MCP Client")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--server-url", default="http://localhost:8000/mcp")
    parser.add_argument("--listen-port", type=int, default=8001)
    parser.add_argument("--demo", action="store_true", help="Run demo directly")
    parser.add_argument("--listen", action="store_true", help="Manual event listener")
    parser.add_argument("--http-listen", action="store_true", help="HTTP event listener")
    
    args = parser.parse_args()
    
    agent = SignalAgent(
        transport=args.transport, 
        server_url=args.server_url,
        listen_port=args.listen_port
    )
    
    try:
        if args.demo:
            await agent.run_demo()
        elif args.listen:
            if await agent.connect():
                await agent.listen_for_events()
            else:
                print("❌ Failed to connect to server")
        elif args.http_listen:
            await agent.listen_for_http_events()
        else:
            await agent.run_interactive()
    finally:
        await agent.close()

if __name__ == "__main__":
    asyncio.run(main())