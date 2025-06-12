# server/server.py
"""
Signal Server - Dual Transport MCP Server for Failure Event Processing

Implements a Model Context Protocol server supporting both stdio and HTTP streamable
transports for intelligent failure event classification and analysis.

Features:
- Dual transport support (stdio/HTTP streamable)  
- Intelligent failure classification and severity assessment
- Automated recommendation generation
- Health monitoring and status verification
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

# MCP imports - organized at top
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent, Tool

# database imports
from database import EventDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# database instance
db = EventDatabase("signal_events.db")

# =============================================================================
# MODELS & SCHEMAS
# =============================================================================

class FailureEvent(BaseModel):
    """Structured failure event model for internal processing."""
    event_id: str
    timestamp: str
    service: str
    severity: str
    message: str
    details: Dict[str, Any] = {}

class FailureEventParameters(BaseModel):
    """Input schema for classify_failure_event tool."""
    event_id: str = Field(..., description="Unique identifier for the failure event")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp when event occurred")
    service: str = Field(..., description="Name of the affected service or system")
    severity: str = Field(..., description="Event severity level: critical, warning, or info")
    message: str = Field(..., description="Human-readable description of the failure")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata and context")

class HealthCheckInput(BaseModel):
    """Input schema for health_check tool."""
    # No parameters needed - health check is parameter-free
    pass

class QueryEventsTodayInput(BaseModel):
    """Input schema for query_events_today tool."""
    # No parameters needed - automatically queries today's events
    pass

class QueryEventsSummaryInput(BaseModel):
    """Input schema for query_events_summary tool."""
    days: int = Field(default=1, description="Number of days to include in summary (default: 1)")

class QueryEventsByServiceInput(BaseModel):
    """Input schema for query_events_by_service tool."""
    service: str = Field(..., description="Name of the service to query events for")
    days: int = Field(default=7, description="Number of days to look back (default: 7)")

    
# =============================================================================
# CORE ANALYSIS ENGINE
# =============================================================================

class FailureAnalyzer:
    """Centralized failure analysis engine with intelligent classification."""
    
    # Classification patterns for different failure types
    SEVERITY_PATTERNS = {
        "critical": ["crash", "down", "failed", "error", "exception", "unavailable", "exhausted"],
        "warning": ["slow", "timeout", "retry", "degraded", "high", "elevated"],
        "info": ["started", "stopped", "completed", "normal", "success"]
    }
    
    CLASSIFICATION_PATTERNS = {
        "database_issue": ["database", "db", "sql", "connection pool", "query", "deadlock"],
        "network_issue": ["network", "connection", "timeout", "unreachable", "circuit breaker"],
        "resource_issue": ["memory", "cpu", "disk", "storage", "capacity", "limit"],
        "security_issue": ["auth", "permission", "unauthorized", "access denied", "suspicious"],
        "service_issue": ["service", "api", "endpoint", "unavailable", "degradation"]
    }
    
    RECOMMENDATIONS = {
        "critical": "Immediate attention required - escalate to on-call engineer",
        "warning": "Monitor closely - investigate if pattern emerges", 
        "info": "Log for analysis - no immediate action required"
    }
    
    @classmethod
    async def analyze_event(cls, event: FailureEvent) -> Dict[str, Any]:
        """
        Comprehensive event analysis pipeline.
        
        Returns complete analysis with severity, classification, and recommendations.
        """
        message_lower = event.message.lower()
        
        # Analyze severity based on message content
        calculated_severity = cls._analyze_severity(message_lower, event.severity)
        
        # Classify event type
        classification = cls._classify_event_type(message_lower)
        
        # Generate recommendation
        recommendation = cls.RECOMMENDATIONS.get(
            calculated_severity, 
            "Review and assess - unknown severity level"
        )
        
        # Create human-readable summary
        summary = cls._format_summary(event, classification, recommendation)
        
        return {
            "event_id": event.event_id,
            "original_severity": event.severity,
            "calculated_severity": calculated_severity,
            "classification": classification,
            "recommendation": recommendation,
            "processed_at": event.timestamp,
            "human_readable": summary,
            "status": "processed"
        }
    
    @classmethod
    def _analyze_severity(cls, message_lower: str, original_severity: str) -> str:
        """Analyze and recalculate event severity based on message content."""
        for severity, keywords in cls.SEVERITY_PATTERNS.items():
            if any(keyword in message_lower for keyword in keywords):
                return severity
        return original_severity.lower()
    
    @classmethod
    def _classify_event_type(cls, message_lower: str) -> str:
        """Classify failure event into operational categories."""
        for event_type, keywords in cls.CLASSIFICATION_PATTERNS.items():
            if any(keyword in message_lower for keyword in keywords):
                return event_type
        return "general_failure"
    
    @classmethod
    def _format_summary(cls, event: FailureEvent, classification: str, recommendation: str) -> str:
        """Format human-readable event analysis summary."""
        return f"""🚨 Signal Alert: {event.event_id}
            Service: {event.service}
            Type: {classification.replace('_', ' ').title()}
            Message: {event.message}
            Action: {recommendation}
            Time: {event.timestamp}""".strip()

# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

async def process_failure_event(event_id: str, timestamp: str, service: str, 
                               severity: str, message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Core failure event processing function used by both transports w/ database storage.
    """
    try:
        # Create event object (existing code)
        event = FailureEvent(
            event_id=event_id,
            timestamp=timestamp,
            service=service,
            severity=severity,
            message=message,
            details=details or {}
        )
        
        logger.info(f"Processing event: {event.event_id} ({event.service})")
        
        # Analyze event through centralized engine (existing code)
        result = await FailureAnalyzer.analyze_event(event)
        
        # *** NEW: Store in database ***
        event_data = {
            "event_id": event_id,
            "timestamp": timestamp,
            "service": service,
            "severity": severity,
            "message": message,
            "details": details or {}
        }
        
        storage_success = db.store_event(event_data, result)
        if storage_success:
            logger.info(f"✅ Event stored in database: {event.event_id}")
        else:
            logger.warning(f"⚠️ Database storage failed for: {event.event_id}")
        
        logger.info(f"Analysis complete: {event.event_id} -> {result['classification']} ({result['calculated_severity']})")
        return result
        
    except Exception as e:
        logger.error(f"Event processing failed: {str(e)}")
        return {
            "error": str(e),
            "status": "failed",
            "event_id": event_id
        }

async def health_check() -> Dict[str, Any]:
    """Health check function used by both transports."""
    return {
        "status": "healthy",
        "service": "signal-server",
        "message": "Signal server operational"
    }

# =============================================================================
# STDIO TRANSPORT IMPLEMENTATION  
# =============================================================================

async def serve_stdio() -> None:
    """Run server with stdio transport using official MCP SDK."""
    logger.info("Starting Signal Server with stdio transport")
    server = Server("signal-server")
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools with schemas."""
        return [
            Tool(
                name="classify_failure_event",
                description="Analyze and classify failure events with intelligent recommendations",
                inputSchema=FailureEventParameters.model_json_schema()
            ),
            Tool(
                name="health_check",
                description="Server health and status verification",
                inputSchema=HealthCheckInput.model_json_schema()
            ),
            # *** NEW DATABASE QUERY TOOLS ***
            Tool(
                name="query_events_today",
                description="Get all events from today with basic analysis",
                inputSchema=QueryEventsTodayInput.model_json_schema()
            ),
            Tool(
                name="query_events_summary",
                description="Get summary statistics for recent events",
                inputSchema=QueryEventsSummaryInput.model_json_schema()
            ),
            Tool(
                name="query_events_by_service",
                description="Get recent events for a specific service",
                inputSchema=QueryEventsByServiceInput.model_json_schema()
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Handle tool calls with unified processing."""
        try:
            if name == "classify_failure_event":
                # Handle both legacy and current parameter formats
                if "event_data" in arguments:
                    # Legacy format - parse JSON string
                    event_dict = json.loads(arguments["event_data"])
                    result = await process_failure_event(
                        event_dict.get("event_id"),
                        event_dict.get("timestamp"), 
                        event_dict.get("service"),
                        event_dict.get("severity"),
                        event_dict.get("message"),
                        event_dict.get("details", {})
                    )
                else:
                    # Current format - direct parameters
                    result = await process_failure_event(
                        arguments.get("event_id"),
                        arguments.get("timestamp"),
                        arguments.get("service"), 
                        arguments.get("severity"),
                        arguments.get("message"),
                        arguments.get("details", {})
                    )
                
            elif name == "health_check":
                result = await health_check()
                result["transport"] = "stdio"

            # *** DATABASE QUERY TOOLS ***
            elif name == "query_events_today":
                events = db.query_events_today()
                summary = db.get_summary_stats(days=1)
                
                result = {
                    "events_today": len(events),
                    "summary": summary,
                    "events": events[:10] if len(events) > 10 else events,  # Limit to 10 for readability
                    "showing": "latest 10" if len(events) > 10 else "all events"
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "query_events_summary":
                days = arguments.get("days", 1)
                summary = db.get_summary_stats(days=days)
                
                result = {
                    "period": f"last {days} day(s)",
                    "summary": summary
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            elif name == "query_events_by_service":
                service = arguments.get("service")
                days = arguments.get("days", 7)
                
                if not service:
                    raise ValueError("service parameter is required")
                    
                events = db.query_events_by_service(service, days)
                
                result = {
                    "service": service,
                    "period": f"last {days} day(s)",
                    "event_count": len(events),
                    "events": events
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
            else:
                raise ValueError(f"Unknown tool: {name}")
            
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            error_result = {"error": str(e), "status": "failed"}
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    # Run server
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

# =============================================================================
# HTTP TRANSPORT IMPLEMENTATION
# =============================================================================

def serve_http_sync() -> None:
    """Run server with HTTP streamable transport using FastMCP."""
    logger.info("Starting Signal Server with HTTP streamable transport")
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
        Analyze and classify failure events with intelligent recommendations.
        
        Processes failure events through multi-stage analysis pipeline providing
        severity assessment, operational classification, and response recommendations.
        """

        # Use the shared process_failure_event function that has database storage
        return await process_failure_event(event_id, timestamp, service, severity, message, details)

    @mcp.tool()
    async def health_check() -> dict:
        """Server health and status verification for monitoring and connectivity testing."""
        return {
            "status": "healthy",
            "service": "signal-server",
            "transport": "http-streamable",
            "message": "Signal server operational"
        }
    
    @mcp.tool()
    async def query_events_today() -> dict:
        """Get all events from today with basic analysis for monitoring and review."""
        try:
            events = db.query_events_today()
            summary = db.get_summary_stats(days=1)
            
            return {
                "events_today": len(events),
                "summary": summary,
                "events": events[:10] if len(events) > 10 else events,
                "showing": "latest 10" if len(events) > 10 else "all events",
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Query events today failed: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }

    @mcp.tool()
    async def query_events_summary(days: int = 1) -> dict:
        """Get summary statistics for recent events over specified time period."""
        try:
            summary = db.get_summary_stats(days=days)
            
            return {
                "period": f"last {days} day(s)",
                "summary": summary,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Query events summary failed: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }

    @mcp.tool()
    async def query_events_by_service(service: str, days: int = 7) -> dict:
        """Get recent events for a specific service over specified time period."""
        try:
            events = db.query_events_by_service(service, days)
            
            return {
                "service": service,
                "period": f"last {days} day(s)",
                "event_count": len(events),
                "events": events,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Query events by service failed: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }

    # Start FastMCP server - restore working API call
    mcp.run("streamable-http")

async def serve_http() -> None:
    """Async wrapper for HTTP server."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, serve_http_sync)

# =============================================================================
# MAIN SERVER INTERFACE
# =============================================================================

async def serve(transport: str = "stdio") -> None:
    """Main server function with transport selection."""
    logger.info(f"Starting Signal Server with {transport} transport")
    
    if transport in ["http", "streamable-http"]:
        await serve_http()
    else:
        await serve_stdio()

# =============================================================================
# BACKWARDS COMPATIBILITY
# =============================================================================

class SignalServer:
    """Backwards compatibility wrapper."""
    
    def start_server(self, transport: str = "stdio"):
        """Start server with automatic event loop handling."""
        try:
            # Check if we're in an event loop
            asyncio.get_running_loop()
            raise RuntimeError(f"Cannot start {transport} server from within running event loop. Use direct execution.")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # Safe to start
                if transport in ["http", "streamable-http"]:
                    serve_http_sync()
                else:
                    asyncio.run(serve_stdio())
            else:
                raise

# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Server - Dual Transport MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http", "streamable-http"], 
                       default="stdio", help="Transport mode")
    
    args = parser.parse_args()
    
    if args.transport in ["http", "streamable-http"]:
        serve_http_sync()
    else:
        asyncio.run(serve_stdio())

if __name__ == "__main__":
    main()