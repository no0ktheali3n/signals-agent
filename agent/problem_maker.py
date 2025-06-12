# problem_maker/problem_maker.py
"""
Problem Maker - Realistic Failure Event Generator

Generates diverse failure scenarios and sends them to Signal Agent via HTTP POST.
Simulates real-world system failures with enhanced realism and contextual metadata.

Features:
- Enhanced failure scenarios with dynamic metadata
- Time-aware event generation patterns
- Realistic service topology and error patterns
- Streamlined architecture for maintainability
"""

import asyncio
import json
import logging
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Any, Dict, List
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# MODELS & DATA
# =============================================================================

class FailureType(Enum):
    """Categories of system failures."""
    DATABASE = "database"
    NETWORK = "network"
    RESOURCE = "resource"
    SECURITY = "security"
    SERVICE = "service"
    INTEGRATION = "integration"

class Severity(Enum):
    """Event severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

@dataclass
class FailureScenario:
    """Template for generating failure events."""
    scenario_id: str
    failure_type: FailureType
    base_severity: Severity
    service_pool: List[str]
    message_templates: List[str]
    probability_weight: float = 1.0

# Enhanced service pools with realistic names
SERVICES = {
    "data": ["user-db", "order-db", "analytics-db", "cache-redis", "search-elastic"],
    "api": ["user-api", "order-api", "payment-api", "notification-api", "auth-service"],
    "infra": ["load-balancer", "api-gateway", "message-queue", "file-storage", "cdn"],
    "external": ["payment-processor", "email-service", "sms-gateway", "monitoring-api"]
}

# =============================================================================
# PROBLEM MAKER
# =============================================================================

class ProblemMaker:
    """
    Generates realistic failure events and sends them to Signal Agent.
    
    Enhanced with dynamic metadata generation and time-aware patterns
    while maintaining lean, efficient architecture.
    """
    
    def __init__(self, agent_url: str = "http://localhost:8001"):
        """Initialize Problem Maker with Signal Agent endpoint."""
        self.agent_url = agent_url.rstrip('/')
        self.events_endpoint = f"{self.agent_url}/events"
        self.health_endpoint = f"{self.agent_url}/health"
        
        self.event_counter = 0
        self.running = False
        self.scenarios = self._build_failure_scenarios()
        
    def _build_failure_scenarios(self) -> List[FailureScenario]:
        """Build comprehensive library of realistic failure scenarios."""
        return [
            # Database Issues
            FailureScenario(
                scenario_id="db_connection_pool",
                failure_type=FailureType.DATABASE,
                base_severity=Severity.CRITICAL,
                service_pool=SERVICES["data"],
                message_templates=[
                    "Connection pool exhausted - {} active of {} max connections",
                    "Database connection timeout after {}ms - pool saturated",
                    "Connection leak detected - {} unclosed connections"
                ],
                probability_weight=2.5
            ),
            
            FailureScenario(
                scenario_id="db_performance", 
                failure_type=FailureType.DATABASE,
                base_severity=Severity.WARNING,
                service_pool=SERVICES["data"],
                message_templates=[
                    "Query execution time {}ms exceeds threshold {}ms",
                    "Slow query on table '{}' - scanning {} rows",
                    "Lock contention detected - {} blocked transactions"
                ],
                probability_weight=2.0
            ),
            
            # Network Issues
            FailureScenario(
                scenario_id="service_connectivity",
                failure_type=FailureType.NETWORK,
                base_severity=Severity.CRITICAL,
                service_pool=SERVICES["api"] + SERVICES["external"],
                message_templates=[
                    "Service {} unreachable - {} consecutive failures",
                    "Circuit breaker opened for {} after {}% error rate",
                    "Upstream timeout from {} - {}ms exceeded"
                ],
                probability_weight=2.2
            ),
            
            # Resource Issues
            FailureScenario(
                scenario_id="resource_exhaustion",
                failure_type=FailureType.RESOURCE,
                base_severity=Severity.WARNING,
                service_pool=SERVICES["api"] + SERVICES["infra"],
                message_templates=[
                    "Memory usage critical - {}% of {} GB allocated",
                    "CPU throttling active - {}% sustained load",
                    "Rate limit exceeded - {} req/sec over {} limit"
                ],
                probability_weight=1.8
            ),
            
            # Security Issues
            FailureScenario(
                scenario_id="security_events",
                failure_type=FailureType.SECURITY,
                base_severity=Severity.CRITICAL,
                service_pool=SERVICES["api"],
                message_templates=[
                    "Authentication failure spike - {}% increase from {}",
                    "Suspicious activity detected - {} failed logins from {}",
                    "Rate limiting aggressive requests - {} attempts blocked"
                ],
                probability_weight=1.3
            ),
            
            # Service Issues
            FailureScenario(
                scenario_id="application_errors",
                failure_type=FailureType.SERVICE,
                base_severity=Severity.WARNING,
                service_pool=SERVICES["api"],
                message_templates=[
                    "Unhandled exception rate elevated - {} errors/min",
                    "Health check failures for {} consecutive attempts",
                    "Service degradation - {}% success rate"
                ],
                probability_weight=2.0
            ),
            
            # Integration Issues
            FailureScenario(
                scenario_id="integration_issues",
                failure_type=FailureType.INTEGRATION,
                base_severity=Severity.WARNING,
                service_pool=SERVICES["external"] + SERVICES["infra"],
                message_templates=[
                    "External service {} returning HTTP {} errors",
                    "Message queue capacity warning - {}% full",
                    "Webhook delivery failures - {} retries exhausted"
                ],
                probability_weight=1.5
            )
        ]
    
    def _generate_enhanced_details(self, scenario: FailureScenario) -> Dict[str, Any]:
        """Generate enhanced, contextual details for failure events."""
        # Get time context for realistic patterns
        now = datetime.now()
        hour, weekday = now.hour, now.weekday()
        time_context = "weekend" if weekday >= 5 else ("business_hours" if 9 <= hour <= 17 else "off_hours")
        
        # Base details
        details = {
            "scenario_type": scenario.scenario_id,
            "failure_category": scenario.failure_type.value,
            "generated_at": now.isoformat(),
            "time_context": time_context,
            "correlation_id": f"req_{random.randint(100000, 999999)}"
        }
        
        # Enhanced scenario-specific details
        if scenario.failure_type == FailureType.DATABASE:
            details.update({
                "database_type": random.choice(["PostgreSQL", "MySQL", "MongoDB", "Redis"]),
                "connection_pool_size": random.choice([10, 20, 50, 100]),
                "active_connections": random.randint(5, 150),
                "query_time_ms": random.randint(100, 10000)
            })
        elif scenario.failure_type == FailureType.NETWORK:
            details.update({
                "response_time_ms": random.randint(1000, 30000),
                "retry_attempts": random.randint(1, 5),
                "error_code": random.choice(["CONN_REFUSED", "TIMEOUT", "DNS_FAILURE", "SSL_ERROR"])
            })
        elif scenario.failure_type == FailureType.RESOURCE:
            details.update({
                "memory_used_gb": round(random.uniform(1, 16), 2),
                "memory_total_gb": random.choice([2, 4, 8, 16, 32]),
                "cpu_percent": round(random.uniform(75, 95), 1)
            })
        elif scenario.failure_type == FailureType.SECURITY:
            details.update({
                "source_ips": [f"192.168.{random.randint(1,255)}.{random.randint(1,255)}" 
                              for _ in range(random.randint(1, 3))],
                "failed_attempts": random.randint(10, 500),
                "auth_method": random.choice(["password", "token", "oauth", "api_key"])
            })
        
        # Common enhanced metrics
        details.update({
            "affected_users": random.choice([40, 120, 400, 1200, 4000]) * random.randint(1, 2),
            "error_rate_percent": round(random.uniform(0.5, 25.0), 2),
            "response_time_p95_ms": random.randint(100, 5000)
        })
        
        return details
    
    def _format_realistic_message(self, template: str, scenario: FailureScenario) -> str:
        """Format message template with contextually appropriate values."""
        placeholder_count = template.count('{}')
        if placeholder_count == 0:
            return template
        
        # Generate values based on failure type context
        if scenario.failure_type == FailureType.DATABASE:
            values = [
                random.randint(15, 100),  # connections
                random.randint(20, 100),  # max connections  
                random.randint(500, 8000),  # timeout ms
                random.choice(["users", "orders", "sessions", "products"])  # table
            ]
        elif scenario.failure_type == FailureType.NETWORK:
            values = [
                random.choice(["payment-api", "user-service", "auth-gateway"]),  # service
                random.randint(3, 10),  # failure count
                random.randint(1000, 30000),  # timeout ms
                random.randint(15, 85)  # error rate %
            ]
        elif scenario.failure_type == FailureType.SECURITY:
            values = [
                random.randint(15, 85),  # percentage
                f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",  # IP
                random.randint(50, 500),  # attempts
                random.choice(["10.0.0.0/8", "suspicious-host.com"])  # source
            ]
        else:
            # Generic realistic values
            values = [
                random.randint(75, 95),  # usage %
                random.randint(4, 32),   # GB/cores
                random.randint(100, 2000),  # rate/count
                random.randint(200, 1000)   # threshold
            ]
        
        return template.format(*values[:placeholder_count])
    
    def generate_event(self) -> Dict[str, Any]:
        """Generate a single realistic failure event with enhanced metadata."""
        # Apply time-based probability adjustment
        current_hour = datetime.now().hour
        adjusted_scenarios = []
        
        for scenario in self.scenarios:
            weight = scenario.probability_weight
            
            # Increase database/resource issues during business hours
            if scenario.failure_type in [FailureType.DATABASE, FailureType.RESOURCE] and 9 <= current_hour <= 17:
                weight *= 1.5
            # Increase security issues during off-hours
            elif scenario.failure_type == FailureType.SECURITY and (current_hour < 9 or current_hour > 17):
                weight *= 1.8
                
            adjusted_scenarios.append((scenario, weight))
        
        # Select scenario based on adjusted weights
        total_weight = sum(w for _, w in adjusted_scenarios)
        random_val = random.uniform(0, total_weight)
        
        cumulative_weight = 0
        for scenario, weight in adjusted_scenarios:
            cumulative_weight += weight
            if random_val <= cumulative_weight:
                selected_scenario = scenario
                break
        else:
            selected_scenario = self.scenarios[0]
        
        # Generate event
        self.event_counter += 1
        # Generate unique event IDs with timestamp
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # microseconds to milliseconds
        event_id = f"{selected_scenario.scenario_id}_{self.event_counter:04d}_{timestamp_str}"
        
        # Realistic timing with slight variance
        time_offset = random.choice([0, 0, 0, 0, 15, 30, 120])  # Mostly current
        timestamp = (datetime.now() - timedelta(seconds=time_offset)).isoformat() + "Z"
        
        service = random.choice(selected_scenario.service_pool)
        
        # Smart severity escalation
        severity = selected_scenario.base_severity.value
        if random.random() < 0.15:  # 15% escalation chance
            if severity == "warning" and selected_scenario.failure_type in [FailureType.DATABASE, FailureType.SECURITY]:
                severity = "critical"
            elif severity == "info":
                severity = "warning"
        
        # Generate realistic message and details
        message_template = random.choice(selected_scenario.message_templates)
        message = self._format_realistic_message(message_template, selected_scenario)
        details = self._generate_enhanced_details(selected_scenario)
        
        return {
            "event_id": event_id,
            "timestamp": timestamp,
            "service": service,
            "severity": severity,
            "message": message,
            "details": details
        }
    
    def check_agent_health(self) -> bool:
        """Check if Signal Agent is healthy and ready."""
        try:
            req = urllib.request.Request(self.health_endpoint)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    health_data = json.loads(response.read().decode())
                    return health_data.get("status") == "healthy" and health_data.get("mcp_connected", False)
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
                logger.error(f"❌ Processing failed: {result.get('error', 'Unknown error') if response.status == 200 else f'HTTP {response.status}'}")
                return False
        except Exception as e:
            logger.error(f"❌ Send error for {event['event_id']}: {str(e)}")
            return False
    
    async def generate_problem_stream(self, count: int = 10, delay_seconds: float = 2.0):
        """Generate stream of failure events and send to Signal Agent."""
        logger.info(f"Starting problem generation - {count} events, {delay_seconds}s intervals")
        
        # Health check
        print("Checking Signal Agent health...")
        if not self.check_agent_health():
            print("Signal Agent not ready. Ensure agent is running with HTTP listener and MCP connected.")
            return
        
        print("✅ Signal Agent ready - starting event generation")
        
        self.running = True
        successful_sends = 0
        
        for i in range(count):
            if not self.running:
                break
            
            event = self.generate_event()
            
            logger.info(f"🚨 Event {i+1}/{count}: {event['event_id']} - {event['severity']} - {event['service']}")
            print(f"📡 Sending: {event['message'][:70]}...")
            
            if self.send_event_to_agent(event):
                successful_sends += 1
                print(f"   ✅ Processed by Signal Agent")
            else:
                print(f"   ❌ Failed to process")
            
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
            print("🔥 PROBLEM MAKER DEMO - ENHANCED EVENTS")
            print("=" * 60)
            for i in range(5):
                event = problem_maker.generate_event()
                print(f"\n📋 Event {i+1}:")
                print(f"ID: {event['event_id']} | Service: {event['service']} | Severity: {event['severity']}")
                print(f"Message: {event['message']}")
                print(f"Context: {event['details']['time_context']} | Users: {event['details']['affected_users']}")
                await asyncio.sleep(1)
        else:
            await problem_maker.generate_problem_stream(
                count=args.count,
                delay_seconds=args.delay
            )
    except KeyboardInterrupt:
        print("\n🛑 Generation interrupted")
        problem_maker.stop_generation()

if __name__ == "__main__":
    asyncio.run(main())