# server/server.py
"""
Signal Server - Dual Transport MCP Server for Failure Event Processing

This module implements a Model Context Protocol (MCP) server that supports both
stdio and HTTP streamable transports for failure event processing through 
intelligent classification and analysis.

The server provides MCP tools for:
- Failure event classification and severity assessment
- Automated recommendation generation
- Health monitoring and status checks

Transport: Supports both stdio (official MCP SDK) and HTTP streamable (FastMCP)
Architecture: Dual implementation with transport selection at runtime
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel

# Configure module logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# INPUT SCHEMA MODELS
# =============================================================================

class FailureEventParameters(BaseModel):
    """Input schema for classify_failure_event tool with direct parameters."""
    event_id: str
    timestamp: str
    service: str
    severity: str
    message: str
    details: Dict[str, Any] = {}

class HealthCheckInput(BaseModel):
    """Input schema for health_check tool - no parameters needed."""
    pass

# =============================================================================
# DATA MODELS
# =============================================================================

class FailureEvent(BaseModel):
    """
    Structured failure event model with validation.
    
    Ensures all incoming events have required fields and proper data types.
    Used for both input validation and internal event processing.
    """
    event_id: str
    timestamp: str
    service: str
    severity: str
    message: str
    details: Dict[str, Any] = {}

# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

async def _analyze_severity(event: FailureEvent) -> str:
    """Analyze and recalculate event severity based on message content."""
    severity_patterns = {
        "critical": ["crash", "down", "failed", "error", "exception", "unavailable"],
        "warning": ["slow", "timeout", "retry", "degraded", "high"],
        "info": ["started", "stopped", "completed", "normal"]
    }
    
    message_lower = event.message.lower()
    
    for severity, keywords in severity_patterns.items():
        if any(keyword in message_lower for keyword in keywords):
            return severity
    
    return event.severity.lower()

async def _classify_event_type(event: FailureEvent) -> str:
    """Classify failure event into operational categories."""
    message_lower = event.message.lower()
    
    classification_patterns = {
        "database_issue": ["database", "db", "sql", "connection pool", "query"],
        "network_issue": ["network", "connection", "timeout", "unreachable"],
        "resource_issue": ["memory", "cpu", "disk", "storage", "capacity"],
        "security_issue": ["auth", "permission", "unauthorized", "access denied"],
        "service_issue": ["service", "api", "endpoint", "unavailable"]
    }
    
    for event_type, keywords in classification_patterns.items():
        if any(keyword in message_lower for keyword in keywords):
            return event_type
    
    return "general_failure"

async def _generate_recommendation(severity: str) -> str:
    """Generate response recommendation based on severity assessment."""
    recommendations = {
        "critical": "Immediate attention required - escalate to on-call engineer",
        "warning": "Monitor closely - investigate if pattern emerges",
        "info": "Log for analysis - no immediate action required"
    }
    
    return recommendations.get(severity, "Review and assess - unknown severity level")

def _format_summary(event: FailureEvent, classification: str, recommendation: str) -> str:
    """Format human-readable event analysis summary."""
    return f"""🚨 Signal Alert: {event.event_id}
Service: {event.service}
Type: {classification.replace('_', ' ').title()}
Message: {event.message}
Action: {recommendation}
Time: {event.timestamp}""".strip()

# =============================================================================
# STDIO SERVER IMPLEMENTATION (Official MCP SDK)
# =============================================================================

async def serve_stdio() -> None:
    """Run server with stdio transport using official MCP SDK."""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
    
    logger.info("Starting Signal Server with stdio transport (Official MCP SDK)")
    
    # Create server instance
    server = Server("signal-server")
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List all available tools with proper schemas."""
        logger.info("DEBUG: stdio list_tools() called")
        tools = [
            Tool(
                name="classify_failure_event",
                description="Primary tool for failure event analysis and classification",
                inputSchema=FailureEventParameters.schema(),
            ),
            Tool(
                name="health_check", 
                description="Server health and status verification tool",
                inputSchema=HealthCheckInput.schema(),
            )
        ]
        logger.info(f"DEBUG: Returning {len(tools)} tools")
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Handle tool calls with proper response formatting."""
        logger.info(f"DEBUG: stdio call_tool called with name='{name}', arguments={arguments}")
        
        try:
            if name == "classify_failure_event":
                # Check if we're getting the old format (event_data string) or new format (direct params)
                if "event_data" in arguments:
                    # Old format - parse JSON string
                    event_data_str = arguments["event_data"]
                    logger.info(f"DEBUG: Old format - parsing event_data string")
                    event_dict = json.loads(event_data_str)
                    
                    # Extract parameters
                    event_id = event_dict.get("event_id")
                    timestamp = event_dict.get("timestamp")
                    service = event_dict.get("service")
                    severity = event_dict.get("severity")
                    message = event_dict.get("message")
                    details = event_dict.get("details", {})
                else:
                    # New format - direct parameters
                    logger.info(f"DEBUG: New format - direct parameters")
                    event_id = arguments.get("event_id")
                    timestamp = arguments.get("timestamp")
                    service = arguments.get("service")
                    severity = arguments.get("severity")
                    message = arguments.get("message")
                    details = arguments.get("details", {})
                
                logger.info(f"DEBUG: Processing event_id={event_id}, service={service}")
                
                # Create FailureEvent object
                event = FailureEvent(
                    event_id=event_id,
                    timestamp=timestamp,
                    service=service,
                    severity=severity,
                    message=message,
                    details=details
                )
                
                logger.info(f"Processing event: {event.event_id}")
                
                # Multi-stage analysis pipeline
                severity_calculated = await _analyze_severity(event)
                classification = await _classify_event_type(event)
                recommendation = await _generate_recommendation(severity_calculated)
                summary = _format_summary(event, classification, recommendation)
                
                # Build comprehensive result
                result = {
                    "event_id": event.event_id,
                    "original_severity": event.severity,
                    "calculated_severity": severity_calculated,
                    "classification": classification,
                    "recommendation": recommendation,
                    "processed_at": event.timestamp,
                    "human_readable": summary,
                    "status": "processed"
                }
                
                logger.info(f"DEBUG: Analysis complete: {result}")
                
                # Return in proper MCP format
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            elif name == "health_check":
                logger.info("DEBUG: health_check called!")
                result = {
                    "status": "healthy",
                    "service": "signal-server", 
                    "transport": "stdio",
                    "message": "Signal server operational"
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            error_result = {
                "error": str(e),
                "status": "failed"
            }
            return [TextContent(
                type="text", 
                text=json.dumps(error_result, indent=2)
            )]

    # Run server with stdio transport
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

# =============================================================================
# HTTP STREAMABLE SERVER IMPLEMENTATION (FastMCP)
# =============================================================================

def serve_http_sync() -> None:
    """Run server with HTTP streamable transport using FastMCP (synchronous)."""
    from mcp.server.fastmcp import FastMCP
    
    logger.info("Starting Signal Server with HTTP streamable transport (FastMCP)")
    
    # Create FastMCP server instance
    mcp = FastMCP("signal-server")
    
    @mcp.tool()
    async def classify_failure_event(
        event_id: str,
        timestamp: str,
        service: str,
        severity: str,
        message: str,
        details: dict = None
    ) -> dict:
        """
        Primary tool for failure event analysis and classification.
        
        Processes incoming failure events through multi-stage analysis using
        FastMCP's native parameter binding for clean, type-safe operation.
        
        Args:
            event_id: Unique identifier for tracking and correlation
            timestamp: ISO 8601 formatted occurrence time
            service: Affected service or system component name  
            severity: Original severity assessment (critical, warning, info)
            message: Human-readable failure description
            details: Additional structured context and metadata (optional)
            
        Returns:
            Comprehensive analysis result including metadata
        """
        logger.info(f"DEBUG: FastMCP classify_failure_event called")
        logger.info(f"DEBUG: event_id={event_id}, service={service}, severity={severity}")
        logger.info(f"DEBUG: message={message}, details={details}")

        try:
            # Handle optional details parameter
            if details is None:
                details = {}
            
            # Create FailureEvent directly from FastMCP parameters
            event = FailureEvent(
                event_id=event_id,
                timestamp=timestamp,
                service=service,
                severity=severity,
                message=message,
                details=details
            )
            logger.info(f"DEBUG: Created FailureEvent: {event}")
            
            logger.info(f"Processing event: {event.event_id}")
            
            # Multi-stage analysis pipeline
            severity_calculated = await _analyze_severity(event)
            logger.info(f"DEBUG: Calculated severity: {severity_calculated}")
            
            classification = await _classify_event_type(event)
            logger.info(f"DEBUG: Classification: {classification}")
            
            recommendation = await _generate_recommendation(severity_calculated)
            logger.info(f"DEBUG: Recommendation: {recommendation}")
            
            summary = _format_summary(event, classification, recommendation)
            logger.info(f"DEBUG: Summary: {summary}")
            
            # Build comprehensive result
            result = {
                "event_id": event.event_id,
                "original_severity": event.severity,
                "calculated_severity": severity_calculated,
                "classification": classification,
                "recommendation": recommendation,
                "processed_at": event.timestamp,
                "human_readable": summary,
                "status": "processed"
            }
            
            logger.info(f"DEBUG: Final result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Processing failed for event: {str(e)}")
            logger.error(f"DEBUG: Exception type: {type(e)}")
            logger.error(f"DEBUG: Exception details: {e}")
            error_result = {
                "error": str(e),
                "status": "failed"
            }
            logger.info(f"DEBUG: Error result: {error_result}")
            return error_result

    @mcp.tool()
    async def health_check() -> dict:
        """
        Server health and status verification tool.
        
        Provides connectivity testing and server status information
        for client handshake operations and monitoring.
        
        Returns:
            Server status and operational information
        """
        logger.info("DEBUG: FastMCP health_check called!")
        result = {
            "status": "healthy",
            "service": "signal-server", 
            "transport": "http-streamable",
            "message": "Signal server operational"
        }
        logger.info(f"DEBUG: health_check result: {json.dumps(result)}")
        
        logger.info(f"DEBUG: Health check returning: {result}")
        return result

    # Run FastMCP server with streamable-http transport
    logger.info("DEBUG: About to call mcp.run('streamable-http')")
    mcp.run("streamable-http")

async def serve_http() -> None:
    """Async wrapper for HTTP server - runs sync FastMCP in executor."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, serve_http_sync)

# =============================================================================
# MAIN SERVER FUNCTION
# =============================================================================

async def serve(transport: str = "stdio") -> None:
    """Main server function with transport selection."""
    logger.info(f"Starting Signal Server with {transport} transport")
    
    if transport == "http" or transport == "streamable-http":
        await serve_http()
    else:
        await serve_stdio()

# =============================================================================
# BACKWARDS COMPATIBILITY WRAPPER
# =============================================================================

class SignalServer:
    """Backwards compatibility wrapper for existing main.py."""
    
    def __init__(self):
        logger.info("DEBUG: SignalServer wrapper initialized")
        
    def start_server(self, transport: str = "stdio"):
        """Start server - handles event loop detection automatically."""
        logger.info(f"Starting Signal Server with {transport} transport")
        
        if transport == "http" or transport == "streamable-http":
            # FastMCP runs synchronously and must be called without event loop
            try:
                # Check if we're in an event loop
                import asyncio
                loop = asyncio.get_running_loop()
                logger.error("❌ Cannot start HTTP server from within running event loop")
                logger.error("💡 Use 'python server/server.py --transport http' instead")
                raise RuntimeError("HTTP server cannot be started from running event loop. Use direct execution.")
            except RuntimeError as e:
                if "no running event loop" in str(e).lower():
                    # No running loop - safe to start FastMCP
                    serve_http_sync()
                else:
                    # Re-raise the error about running event loop
                    raise
        else:
            # For stdio, need to handle event loop properly  
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                logger.error("❌ Cannot start stdio server from within running event loop")
                logger.error("💡 Use 'python server/server.py --transport stdio' instead")
                raise RuntimeError("stdio server cannot be started from running event loop. Use direct execution.")
            except RuntimeError as e:
                if "no running event loop" in str(e).lower():
                    # No running loop - safe to start
                    asyncio.run(serve_stdio())
                else:
                    # Re-raise the error about running event loop
                    raise

# =============================================================================
# ASYNC WRAPPER FOR MAIN.PY
# =============================================================================

async def serve_async(transport: str = "stdio") -> None:
    """Async wrapper for main.py integration."""
    if transport == "http" or transport == "streamable-http":
        # For HTTP, run the sync FastMCP server in executor
        await serve_http()
    else:
        # stdio can run directly in async context
        await serve_stdio()

# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

def main():
    """Main entry point for standalone server execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Server - Dual Transport MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http", "streamable-http"], default="stdio",
                      help="Transport mode (stdio, http, or streamable-http)")
    
    args = parser.parse_args()
    logger.info(f"Starting server with {args.transport} transport")
    
    if args.transport == "http" or args.transport == "streamable-http":
        # FastMCP runs synchronously
        asyncio.run(serve_http())
    else:
        asyncio.run(serve_stdio())

if __name__ == "__main__":
    main()