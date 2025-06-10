# problem_maker/problem_maker.py
"""
Problem Maker - Realistic Failure Event Generator

Generates diverse, realistic failure scenarios and sends them to Signal Agent
via HTTP POST. Simulates real-world system failures with dynamic patterns,
cascading effects, and time-based variations.

Features:
- Realistic failure scenarios with dynamic metadata
- Time-aware event generation (business hours, weekends, etc.)
- Cascading failure patterns and correlations
- Load-balanced service pools with realistic naming
- Advanced failure details with contextual information
"""

import asyncio
import json
import logging
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# FAILURE TAXONOMY & MODELS
# =============================================================================

class FailureType(Enum):
    """Categories of system failures."""
    DATABASE = "database"
    NETWORK = "network" 
    RESOURCE = "resource"
    SECURITY = "security"
    SERVICE = "service"
    INTEGRATION = "integration"
    INFRASTRUCTURE = "infrastructure"
    DATA = "data"

class Severity(Enum):
    """Event severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

@dataclass
class FailureScenario:
    """Template for generating realistic failure events."""
    scenario_id: str
    failure_type: FailureType
    base_severity: Severity
    service_pool: List[str]
    message_templates: List[str]
    probability_weight: float = 1.0
    time_bias: Optional[str] = None  # "business_hours", "off_hours", "weekend"

# =============================================================================
# REALISTIC DATA GENERATORS
# =============================================================================

class RealisticDataGenerator:
    """Generates realistic failure metadata and contextual information."""
    
    # Service topology - realistic microservice names
    SERVICES = {
        "frontend": ["web-app", "mobile-app", "admin-portal", "customer-portal"],
        "api": ["user-api", "order-api", "payment-api", "notification-api", "search-api"],
        "data": ["user-db", "order-db", "analytics-db", "cache-redis", "search-elastic"],
        "infra": ["load-balancer", "api-gateway", "message-queue", "file-storage"],
        "external": ["payment-processor", "email-service", "sms-gateway", "cdn"]
    }
    
    # Common error patterns
    ERROR_CODES = {
        "database": ["CONN_POOL_EXHAUSTED", "DEADLOCK_DETECTED", "TIMEOUT", "SCHEMA_ERROR"],
        "network": ["CONN_REFUSED", "TIMEOUT", "DNS_FAILURE", "SSL_ERROR", "CIRCUIT_OPEN"],
        "resource": ["OUT_OF_MEMORY", "CPU_THROTTLED", "DISK_FULL", "RATE_LIMITED"],
        "security": ["AUTH_FAILED", "TOKEN_EXPIRED", "PERMISSION_DENIED", "SUSPICIOUS_ACTIVITY"]
    }
    
    @staticmethod
    def get_time_context():
        """Get current time context for realistic failure patterns."""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        if weekday >= 5:  # Weekend
            return "weekend"
        elif 9 <= hour <= 17:  # Business hours
            return "business_hours"
        else:
            return "off_hours"
    
    @staticmethod
    def generate_service_metrics():
        """Generate realistic service metrics."""
        return {
            "request_rate_per_sec": random.randint(10, 1000),
            "response_time_p95_ms": random.randint(50, 2000),
            "error_rate_percent": round(random.uniform(0.1, 15.0), 2),
            "active_connections": random.randint(5, 500),
            "cpu_percent": round(random.uniform(10, 95), 1),
            "memory_percent": round(random.uniform(20, 90), 1)
        }
    
    @staticmethod
    def generate_correlation_id():
        """Generate realistic correlation ID."""
        import uuid
        return f"req_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def generate_affected_users():
        """Generate realistic user impact data."""
        base_users = random.choice([50, 150, 500, 1500, 5000])
        # Add some realistic variance
        variance = random.uniform(0.8, 1.3)
        return int(base_users * variance)

# =============================================================================
# PROBLEM MAKER
# =============================================================================

class ProblemMaker:
    """
    Generates realistic failure events and sends them to Signal Agent.
    
    Simulates real-world monitoring systems with dynamic failure patterns,
    contextual metadata, and time-aware event generation.
    """
    
    def __init__(self, agent_url: str = "http://localhost:8001"):
        """Initialize Problem Maker with Signal Agent endpoint."""
        self.agent_url = agent_url.rstrip('/')
        self.events_endpoint = f"{self.agent_url}/events"
        self.health_endpoint = f"{self.agent_url}/health"
        
        self.event_counter = 0
        self.running = False
        
        # Initialize data generator
        self.data_gen = RealisticDataGenerator()
        
        # Build scenarios after data_gen is available
        self.scenarios = self._build_failure_scenarios()
        
    def _build_failure_scenarios(self) -> List[FailureScenario]:
        """Build comprehensive library of realistic failure scenarios."""
        
        return [
            # Database Issues (Higher probability during business hours)
            FailureScenario(
                scenario_id="db_connection_pool",
                failure_type=FailureType.DATABASE,
                base_severity=Severity.CRITICAL,
                service_pool=self.data_gen.SERVICES["data"],
                message_templates=[
                    "Connection pool exhausted - {} active of {} max connections",
                    "Database connection timeout after {}ms - pool saturated",
                    "Connection leak detected - {} unclosed connections",
                    "Pool exhaustion causing {} queued requests"
                ],
                probability_weight=3.0,
                time_bias="business_hours"
            ),
            
            FailureScenario(
                scenario_id="db_performance",
                failure_type=FailureType.DATABASE,
                base_severity=Severity.WARNING,
                service_pool=self.data_gen.SERVICES["data"],
                message_templates=[
                    "Query execution time {}ms exceeds threshold {}ms",
                    "Slow query on table '{}' - scanning {} rows",
                    "Index missing for frequent query pattern",
                    "Lock contention detected - {} blocked transactions"
                ],
                probability_weight=2.5
            ),
            
            # Network Issues (Higher during deployments/updates)
            FailureScenario(
                scenario_id="service_connectivity",
                failure_type=FailureType.NETWORK,
                base_severity=Severity.CRITICAL,
                service_pool=self.data_gen.SERVICES["api"] + self.data_gen.SERVICES["external"],
                message_templates=[
                    "Service {} unreachable - {} consecutive failures",
                    "Circuit breaker opened for {} after {}% error rate",
                    "Upstream timeout from {} - {}ms exceeded",
                    "Load balancer marked {} unhealthy"
                ],
                probability_weight=2.8
            ),
            
            # Resource Issues (More common during high load)
            FailureScenario(
                scenario_id="resource_exhaustion",
                failure_type=FailureType.RESOURCE,
                base_severity=Severity.WARNING,
                service_pool=self.data_gen.SERVICES["api"] + self.data_gen.SERVICES["frontend"],
                message_templates=[
                    "Memory usage critical - {}% of {} GB allocated",
                    "CPU throttling active - {}% sustained load",
                    "Disk space low - {} GB remaining of {} GB",
                    "Rate limit exceeded - {} requests/sec over {} limit"
                ],
                probability_weight=2.2,
                time_bias="business_hours"
            ),
            
            # Security Issues (Often during off-hours)
            FailureScenario(
                scenario_id="security_events",
                failure_type=FailureType.SECURITY,
                base_severity=Severity.CRITICAL,
                service_pool=self.data_gen.SERVICES["api"] + self.data_gen.SERVICES["frontend"],
                message_templates=[
                    "Authentication failure spike - {}% increase from {}",
                    "Suspicious activity detected - {} failed logins",
                    "Rate limiting aggressive requests from {}",
                    "Token validation failures increased {}%"
                ],
                probability_weight=1.5,
                time_bias="off_hours"
            ),
            
            # Service Issues
            FailureScenario(
                scenario_id="application_errors",
                failure_type=FailureType.SERVICE,
                base_severity=Severity.WARNING,
                service_pool=self.data_gen.SERVICES["api"],
                message_templates=[
                    "Unhandled exception rate elevated - {} errors/min",
                    "Health check failures for {} consecutive attempts",
                    "Service degradation - {}% success rate",
                    "Startup failures in {} environment"
                ],
                probability_weight=2.0
            ),
            
            # Infrastructure Issues (Often weekends during maintenance)
            FailureScenario(
                scenario_id="infrastructure_issues",
                failure_type=FailureType.INFRASTRUCTURE,
                base_severity=Severity.WARNING,
                service_pool=self.data_gen.SERVICES["infra"],
                message_templates=[
                    "Load balancer unhealthy - {} of {} nodes down",
                    "Message queue capacity warning - {}% full",
                    "File storage latency increased - {}ms average",
                    "CDN cache miss rate elevated to {}%"
                ],
                probability_weight=1.8,
                time_bias="weekend"
            ),
            
            # Data Issues
            FailureScenario(
                scenario_id="data_quality",
                failure_type=FailureType.DATA,
                base_severity=Severity.WARNING,
                service_pool=self.data_gen.SERVICES["data"],
                message_templates=[
                    "Data validation failures increased {}%",
                    "Schema migration warning - {} affected records",
                    "Backup verification failed for {} dataset",
                    "Data consistency check found {} discrepancies"
                ],
                probability_weight=1.2
            )
        ]
    
    def _generate_dynamic_details(self, scenario: FailureScenario) -> Dict[str, Any]:
        """Generate dynamic, contextual details for failure events."""
        details = {
            "scenario_type": scenario.scenario_id,
            "failure_category": scenario.failure_type.value,
            "generated_at": datetime.now().isoformat(),
            "correlation_id": self.data_gen.generate_correlation_id(),
            "time_context": self.data_gen.get_time_context()
        }
        
        # Add scenario-specific details
        if scenario.failure_type == FailureType.DATABASE:
            details.update({
                "database_type": random.choice(["PostgreSQL", "MySQL", "MongoDB", "Redis"]),
                "connection_pool_size": random.choice([10, 20, 50, 100]),
                "active_connections": random.randint(5, 150),
                "query_time_ms": random.randint(100, 10000),
                "affected_tables": random.randint(1, 5)
            })
        
        elif scenario.failure_type == FailureType.NETWORK:
            details.update({
                "response_time_ms": random.randint(1000, 30000),
                "retry_attempts": random.randint(1, 5),
                "error_code": random.choice(self.data_gen.ERROR_CODES["network"]),
                "affected_regions": random.randint(1, 3)
            })
        
        elif scenario.failure_type == FailureType.RESOURCE:
            details.update({
                "memory_used_gb": round(random.uniform(1, 16), 2),
                "memory_total_gb": random.choice([2, 4, 8, 16, 32]),
                "cpu_cores": random.choice([2, 4, 8, 16]),
                "disk_used_percent": round(random.uniform(70, 95), 1)
            })
        
        elif scenario.failure_type == FailureType.SECURITY:
            details.update({
                "source_ips": [f"192.168.{random.randint(1,255)}.{random.randint(1,255)}" 
                              for _ in range(random.randint(1, 3))],
                "failed_attempts": random.randint(10, 500),
                "auth_method": random.choice(["password", "token", "oauth", "api_key"]),
                "user_agent": random.choice(["bot", "browser", "api_client", "unknown"])
            })
        
        # Add common service metrics
        details.update(self.data_gen.generate_service_metrics())
        details["affected_users"] = self.data_gen.generate_affected_users()
        
        return details
    
    def _apply_time_bias(self, scenarios: List[FailureScenario]) -> List[FailureScenario]:
        """Apply time-based probability bias to scenarios."""
        current_context = self.data_gen.get_time_context()
        
        adjusted_scenarios = []
        for scenario in scenarios:
            weight = scenario.probability_weight
            
            # Adjust weight based on time bias
            if scenario.time_bias == current_context:
                weight *= 2.0  # Double probability during biased time
            elif scenario.time_bias and scenario.time_bias != current_context:
                weight *= 0.5  # Halve probability during non-biased time
            
            adjusted_scenarios.append(FailureScenario(
                scenario.scenario_id, scenario.failure_type, scenario.base_severity,
                scenario.service_pool, scenario.message_templates, weight, scenario.time_bias
            ))
        
        return adjusted_scenarios
    
    def generate_event(self) -> Dict[str, Any]:
        """Generate a single realistic failure event with dynamic content."""
        # Apply time-based scenario selection
        time_adjusted_scenarios = self._apply_time_bias(self.scenarios)
        
        # Select scenario based on adjusted weights
        total_weight = sum(s.probability_weight for s in time_adjusted_scenarios)
        random_val = random.uniform(0, total_weight)
        
        cumulative_weight = 0
        selected_scenario = None
        for scenario in time_adjusted_scenarios:
            cumulative_weight += scenario.probability_weight
            if random_val <= cumulative_weight:
                selected_scenario = scenario
                break
        
        selected_scenario = selected_scenario or time_adjusted_scenarios[0]
        
        # Generate event components
        self.event_counter += 1
        event_id = f"{selected_scenario.scenario_id}_{self.event_counter:04d}"
        
        # Realistic timing - slight variance for realism
        time_offset = random.choice([0, 0, 0, 0, 0, 15, 30, 60, 180])  # Mostly current
        timestamp = (datetime.now() - timedelta(seconds=time_offset)).isoformat() + "Z"
        
        service = random.choice(selected_scenario.service_pool)
        
        # Dynamic severity escalation based on time and failure type
        severity = selected_scenario.base_severity.value
        if random.random() < 0.12:  # 12% escalation chance
            if severity == "warning" and selected_scenario.failure_type in [FailureType.DATABASE, FailureType.SECURITY]:
                severity = "critical"
            elif severity == "info":
                severity = "warning"
        
        # Generate dynamic message with realistic values
        message_template = random.choice(selected_scenario.message_templates)
        message = self._format_message(message_template, selected_scenario)
        
        # Generate rich, contextual details
        details = self._generate_dynamic_details(selected_scenario)
        
        return {
            "event_id": event_id,
            "timestamp": timestamp,
            "service": service,
            "severity": severity,
            "message": message,
            "details": details
        }
    
    def _format_message(self, template: str, scenario: FailureScenario) -> str:
        """Format message template with realistic values."""
        # Count placeholders
        placeholder_count = template.count('{}')
        
        if placeholder_count == 0:
            return template
        
        values = []
        
        # Generate contextual values based on failure type
        if scenario.failure_type == FailureType.DATABASE:
            values.extend([
                random.randint(8, 100),  # connections/pool size
                random.randint(10, 100),  # max connections
                random.randint(500, 5000),  # timeout ms
                random.choice(["users", "orders", "sessions", "products"])  # table name
            ])
        elif scenario.failure_type == FailureType.NETWORK:
            values.extend([
                random.choice(["payment-api", "user-service", "auth-gateway"]),  # service name
                random.randint(3, 10),  # failure count
                random.randint(1000, 30000),  # timeout ms
                random.randint(15, 85)  # error rate %
            ])
        elif scenario.failure_type == FailureType.RESOURCE:
            values.extend([
                random.randint(75, 95),  # usage %
                random.randint(4, 32),  # total GB/cores
                random.randint(100, 1000),  # rate limit
                random.randint(200, 2000)  # current rate
            ])
        else:
            # Generic values for other types
            values.extend([
                random.randint(10, 500),
                random.randint(1, 10),
                random.randint(100, 5000),
                random.randint(5, 50)
            ])
        
        # Use only the number of values we need
        return template.format(*values[:placeholder_count])
    
    def check_agent_health(self) -> bool:
        """Check if Signal Agent is healthy and ready."""
        try:
            req = urllib.request.Request(self.health_endpoint)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    health_data = json.loads(response.read().decode())
                    is_healthy = health_data.get("status") == "healthy"
                    mcp_connected = health_data.get("mcp_connected", False)
                    
                    if is_healthy and mcp_connected:
                        logger.info("✅ Signal Agent is healthy and connected")
                        return True
                    else:
                        logger.warning("⚠️ Signal Agent not ready for events")
                        return False
                else:
                    logger.error(f"❌ Health check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Health check error: {str(e)}")
            return False
    
    def send_event_to_agent(self, event: Dict[str, Any]) -> bool:
        """Send event to Signal Agent via HTTP POST."""
        try:
            event_json = json.dumps(event).encode('utf-8')
            req = urllib.request.Request(
                self.events_endpoint,
                data=event_json,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode())
                    if result.get("status") == "processed":
                        logger.info(f"✅ Event {event['event_id']} processed successfully")
                        return True
                    else:
                        logger.error(f"❌ Processing failed: {result.get('error')}")
                        return False
                else:
                    logger.error(f"❌ HTTP {response.status}: {response.read().decode()}")
                    return False
        except Exception as e:
            logger.error(f"❌ Send error for {event['event_id']}: {str(e)}")
            return False
    
    async def generate_problem_stream(self, count: int = 10, delay_seconds: float = 2.0):
        """Generate stream of failure events and send to Signal Agent."""
        logger.info(f"🔥 Starting problem generation - {count} events, {delay_seconds}s intervals")
        logger.info(f"🎯 Target: {self.agent_url}")
        
        # Health check
        print("🔍 Checking Signal Agent health...")
        if not self.check_agent_health():
            print("❌ Signal Agent not ready. Ensure:")
            print("   • Signal Agent HTTP listener running")
            print("   • Signal Server connected via MCP")
            print(f"   • Agent accessible at {self.agent_url}")
            return
        
        print("✅ Signal Agent ready - starting event generation")
        
        self.running = True
        successful_sends = 0
        
        for i in range(count):
            if not self.running:
                break
            
            # Generate realistic event
            event = self.generate_event()
            
            logger.info(f"🚨 Event {i+1}/{count}: {event['event_id']} - {event['severity']} - {event['service']}")
            print(f"📡 Sending: {event['message'][:70]}...")
            
            # Send to agent
            if self.send_event_to_agent(event):
                successful_sends += 1
                print(f"   ✅ Processed by Signal Agent")
            else:
                print(f"   ❌ Failed to process")
            
            # Wait before next event
            if i < count - 1:
                await asyncio.sleep(delay_seconds)
        
        success_rate = (successful_sends / count) * 100 if count > 0 else 0
        logger.info(f"🎉 Generation complete: {successful_sends}/{count} events ({success_rate:.1f}% success)")
        self.running = False
    
    def stop_generation(self):
        """Stop problem generation."""
        self.running = False
        logger.info("🛑 Problem generation stopped")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main entry point for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Problem Maker - Realistic Failure Event Generator")
    parser.add_argument("--agent-url", default="http://localhost:8001", help="Signal Agent endpoint")
    parser.add_argument("--count", type=int, default=10, help="Number of events to generate")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between events (seconds)")
    parser.add_argument("--demo", action="store_true", help="Show sample events without sending")
    parser.add_argument("--health", action="store_true", help="Check Agent health and exit")
    
    args = parser.parse_args()
    
    problem_maker = ProblemMaker(agent_url=args.agent_url)
    
    try:
        if args.health:
            print("🔍 Checking Signal Agent health...")
            is_healthy = problem_maker.check_agent_health()
            print("✅ Signal Agent ready" if is_healthy else "❌ Signal Agent not ready")
            exit(0 if is_healthy else 1)
            
        elif args.demo:
            print("UNLEASH THE PROBLEMS!")
            print("=" * 60)
            for i in range(5):
                event = problem_maker.generate_event()
                print(f"\n📋 Event {i+1}:")
                print(f"ID: {event['event_id']}")
                print(f"Service: {event['service']} | Severity: {event['severity']}")
                print(f"Message: {event['message']}")
                print(f"Time Context: {event['details']['time_context']}")
                print(f"Affected Users: {event['details']['affected_users']}")
                await asyncio.sleep(1)
        else:
            # Generate and send events
            await problem_maker.generate_problem_stream(
                count=args.count,
                delay_seconds=args.delay
            )
    except KeyboardInterrupt:
        print("\n🛑 Generation interrupted")
        problem_maker.stop_generation()

if __name__ == "__main__":
    asyncio.run(main())