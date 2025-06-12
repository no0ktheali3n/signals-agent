# server/database.py
"""
Simple SQLite database layer for Signal Server event storage.
Designed for quick setup with zero external dependencies.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class EventDatabase:
    """Simple SQLite database for storing and querying failure events."""
    
    def __init__(self, db_path: str = "signal_events.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    service TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,  -- JSON string
                    classification TEXT,
                    calculated_severity TEXT,
                    recommendation TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    processed_at TEXT
                )
            """)
            
            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_service ON events(service)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON events(severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
            
            conn.commit()
            logger.info("✅ Database initialized successfully")
    
    def store_event(self, event_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> bool:
        """Store original event and analysis results."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO events 
                    (event_id, timestamp, service, severity, message, details, 
                     classification, calculated_severity, recommendation, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_data.get('event_id'),
                    event_data.get('timestamp'),
                    event_data.get('service'),
                    event_data.get('severity'),
                    event_data.get('message'),
                    json.dumps(event_data.get('details', {})),
                    analysis_result.get('classification'),
                    analysis_result.get('calculated_severity'),
                    analysis_result.get('recommendation'),
                    analysis_result.get('processed_at')
                ))
                conn.commit()
                logger.info(f"✅ Stored event: {event_data.get('event_id')}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to store event: {str(e)}")
            return False
    
    def query_events_today(self) -> List[Dict[str, Any]]:
        """Get events from the last 24 hours."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM events 
                    WHERE datetime(timestamp) >= datetime('now', '-24 hours')
                    ORDER BY timestamp DESC
                """)
                
                events = []
                for row in cursor.fetchall():
                    event = dict(row)
                    if event['details']:
                        event['details'] = json.loads(event['details'])
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"❌ Query failed: {str(e)}")
            return []
    
    def query_events_by_service(self, service: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent events for a specific service."""
        try:
            hours = days * 24
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM events 
                    WHERE service = ? AND datetime(timestamp) >= datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                """.format(hours), (service,))
                
                events = []
                for row in cursor.fetchall():
                    event = dict(row)
                    if event['details']:
                        event['details'] = json.loads(event['details'])
                    events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"❌ Service query failed: {str(e)}")
            return []
    
    def get_summary_stats(self, days: int = 1) -> Dict[str, Any]:
        """Get basic summary statistics for recent events."""
        try:
            # TEMPORARY: Remove time filter to test
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Total events - NO TIME FILTER
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_events,
                        COUNT(CASE WHEN calculated_severity = 'critical' THEN 1 END) as critical_count,
                        COUNT(CASE WHEN calculated_severity = 'warning' THEN 1 END) as warning_count,
                        COUNT(CASE WHEN calculated_severity = 'info' THEN 1 END) as info_count,
                        COUNT(DISTINCT service) as affected_services
                    FROM events
                """)
                
                stats = dict(cursor.fetchone())
                
                # Most affected services - NO TIME FILTER
                cursor = conn.execute("""
                    SELECT service, COUNT(*) as event_count
                    FROM events
                    GROUP BY service
                    ORDER BY event_count DESC
                    LIMIT 5
                """)
                
                stats['top_services'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Stats query failed: {str(e)}")
            return {}

# Integration point for server.py
def integrate_database_into_server():
    """
    Here's how to modify your existing server.py to add database storage:
    
    1. Add this import at the top:
       from database import EventDatabase
    
    2. Initialize database in your server:
       db = EventDatabase()
    
    3. Modify your process_failure_event function to store results:
       
       async def process_failure_event(event_id, timestamp, service, severity, message, details=None):
           # ... existing processing logic ...
           result = await FailureAnalyzer.analyze_event(event)
           
           # NEW: Store in database
           event_data = {
               "event_id": event_id,
               "timestamp": timestamp,
               "service": service,
               "severity": severity,
               "message": message,
               "details": details or {}
           }
           db.store_event(event_data, result)
           
           return result
    
    4. Add new MCP tools for querying:
       
       @server.call_tool()
       async def call_tool(name: str, arguments: dict):
           # ... existing tools ...
           elif name == "query_events_today":
               events = db.query_events_today()
               return [TextContent(type="text", text=json.dumps({
                   "events": events,
                   "count": len(events)
               }, indent=2))]
           
           elif name == "get_event_summary":
               stats = db.get_summary_stats()
               return [TextContent(type="text", text=json.dumps(stats, indent=2))]
    """
    pass

# Simple test function
def test_database():
    """Quick test to verify database works."""
    db = EventDatabase("test_events.db")
    
    # Test data
    test_event = {
        "event_id": "test_001",
        "timestamp": "2025-06-11T10:30:00Z",
        "service": "test-service",
        "severity": "warning",
        "message": "Test database storage",
        "details": {"test": True}
    }
    
    test_analysis = {
        "classification": "service_issue",
        "calculated_severity": "warning",
        "recommendation": "Monitor closely",
        "processed_at": "2025-06-11T10:30:00Z"
    }
    
    # Store and retrieve
    success = db.store_event(test_event, test_analysis)
    if success:
        events = db.query_events_today()
        stats = db.get_summary_stats()
        print(f"✅ Database test passed! Found {len(events)} events")
        print(f"📊 Stats: {stats}")
        
        # Show actual data in readable format
        print("\n" + "="*60)
        print("STORED EVENTS (Human Readable)")
        print("="*60)
        for event in events:
            print(f"ID: {event['event_id']}")
            print(f"Service: {event['service']} | Severity: {event['calculated_severity']}")
            print(f"Message: {event['message']}")
            print(f"Classification: {event['classification']}")
            print(f"Time: {event['timestamp']}")
            print("-" * 40)
    else:
        print("❌ Database test failed")

def view_database(db_file="test_events.db"):
    """Simple viewer for your SQLite database - run this anytime to see what's stored."""
    try:
        db = EventDatabase(db_file)
        events = db.query_events_today()
        stats = db.get_summary_stats()
        
        print(f"\n{'='*70}")
        print(f"DATABASE VIEWER: {db_file}")
        print(f"{'='*70}")
        
        print(f"\n📊 SUMMARY STATS:")
        print(f"Total Events: {stats.get('total_events', 0)}")
        print(f"Critical: {stats.get('critical_count', 0)} | Warning: {stats.get('warning_count', 0)} | Info: {stats.get('info_count', 0)}")
        print(f"Affected Services: {stats.get('affected_services', 0)}")
        
        if stats.get('top_services'):
            print(f"\n🔥 TOP AFFECTED SERVICES:")
            for service in stats['top_services']:
                print(f"   {service['service']}: {service['event_count']} events")
        
        print(f"\n📋 TODAY'S EVENTS ({len(events)} total):")
        print("-" * 70)
        
        if not events:
            print("No events found for today")
        else:
            for i, event in enumerate(events, 1):
                print(f"{i}. {event['event_id']} | {event['service']} | {event['calculated_severity'].upper()}")
                print(f"   {event['message']}")
                print(f"   🕒 {event['timestamp']} | 🏷️ {event['classification']}")
                if i < len(events):
                    print()
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error viewing database: {str(e)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "view":
        # python database.py view [optional_db_file]
        db_file = sys.argv[2] if len(sys.argv) > 2 else "test_events.db"
        view_database(db_file)
    else:
        # python database.py (run test)
        test_database()