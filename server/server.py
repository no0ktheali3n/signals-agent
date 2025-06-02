# server/server.py
"""
Signal Server - Official MCP SDK Server for Failure Event Processing

This module implements a Model Context Protocol (MCP) server using the official
MCP SDK that processes failure events through intelligent classification and analysis.

The server provides MCP tools for:
- Failure event classification and severity assessment
- Automated recommendation generation
- Health monitoring and status checks

Transport: Uses stdio for reliable MCP communication
Architecture: Official MCP SDK with proper tool registration and schemas
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel

# Configure module logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# INPUT SCHEMA MODELS (LIKE GIT SERVER)
# =============================================================================

class FailureEventInput(BaseModel):
    """Input schema for classify_failure_event tool."""
    event_data: str

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
# ANALYSIS FUNCTIONS (PRESERVED FROM YOUR CODE)
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
    return f"""
        🚨 Signal Alert: {event.event_id}
        Service: {event.service}
        Type: {classification.replace('_', ' ').title()}
        Message: {event.message}
        Action: {recommendation}
        Time: {event.timestamp}
    """.strip()

# =============================================================================
# MAIN SERVER FUNCTION (FOLLOWING GIT SERVER PATTERN)
# =============================================================================

async def serve() -> None:
    """Main server function using official MCP SDK pattern."""
    logger.info("Starting Signal Server with official MCP SDK")
    
    # Create server instance (like Git server)
    server = Server("signal-server")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools with proper schemas."""
        logger.info("DEBUG: list_tools() called")
        tools = [
            Tool(
                name="classify_failure_event",
                description="Primary tool for failure event analysis and classification",
                inputSchema=FailureEventInput.schema(),
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
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls with proper response formatting."""
        logger.info(f"DEBUG: call_tool called with name='{name}', arguments={arguments}")
        
        try:
            if name == "classify_failure_event":
                event_data = arguments["event_data"]
                logger.info(f"DEBUG: Processing event_data: {event_data}")
                
                # Parse and validate event data
                event_dict = json.loads(event_data)
                event = FailureEvent(**event_dict)
                
                logger.info(f"Processing event: {event.event_id}")
                
                # Multi-stage analysis pipeline
                severity = await _analyze_severity(event)
                classification = await _classify_event_type(event)
                recommendation = await _generate_recommendation(severity)
                summary = _format_summary(event, classification, recommendation)
                
                # Build comprehensive result
                result = {
                    "event_id": event.event_id,
                    "original_severity": event.severity,
                    "calculated_severity": severity,
                    "classification": classification,
                    "recommendation": recommendation,
                    "processed_at": event.timestamp,
                    "human_readable": summary,
                    "status": "processed"
                }
                
                logger.info(f"DEBUG: Analysis complete: {result}")
                
                # Return in proper MCP format (like Git server)
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

    # Run server with stdio transport (like Git server)
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

# =============================================================================
# BACKWARDS COMPATIBILITY WRAPPER
# =============================================================================

class SignalServer:
    """Backwards compatibility wrapper for existing main.py."""
    
    def __init__(self):
        logger.info("DEBUG: SignalServer wrapper initialized")
        
    def start_server(self, transport: str = "stdio"):
        """Start server using asyncio."""
        logger.info(f"Starting Signal Server with {transport} transport")
        asyncio.run(serve())

# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

def main():
    """Main entry point for standalone server execution."""
    logger.info("DEBUG: Main entry point called")
    asyncio.run(serve())

if __name__ == "__main__":
    main()