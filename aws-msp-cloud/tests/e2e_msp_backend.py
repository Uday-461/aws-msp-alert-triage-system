#!/usr/bin/env python3
"""
E2E Test for MSP Backend Service
Tests the complete alert processing pipeline locally
"""
import asyncio
import asyncpg
import httpx
import json
import websockets
from datetime import datetime, timedelta
import uuid

# Configuration
DATABASE_URL = "postgresql://postgres:hackathon_db_pass@localhost:5432/superops"
API_BASE_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws"

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_section(msg):
    print(f"\n{YELLOW}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{RESET}\n")

async def cleanup_test_data(conn):
    """Remove test data from database"""
    print_info("Cleaning up test data...")
    await conn.execute("DELETE FROM audit.action_logs WHERE performed_by = 'e2e-test'")
    await conn.execute("DELETE FROM superops.ml_classifications WHERE alert_id LIKE 'e2e-test-%'")
    await conn.execute("DELETE FROM superops.alerts WHERE alert_id LIKE 'e2e-test-%'")
    print_success("Test data cleaned up")

async def create_test_alerts(conn):
    """Insert test alerts into database"""
    print_info("Creating test alerts...")

    # Get first client for test alerts
    client_row = await conn.fetchrow("SELECT id FROM superops.clients LIMIT 1")
    client_id = client_row['id']

    # Get first asset for test alerts
    asset_row = await conn.fetchrow("SELECT id FROM superops.assets WHERE client_id = $1 LIMIT 1", client_id)
    asset_id = asset_row['id'] if asset_row else None

    # Create test alerts
    alert_ids = []  # Will store VARCHAR alert_id values
    alert_uuids = []  # Will store UUID id values
    severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    messages = [
        'CPU usage at 95% for 10 minutes',
        'Memory usage critical - 98% on DB-01',
        'Disk space low on /var partition',
        'Network latency spike detected'
    ]

    for i in range(4):
        alert_id_str = f"e2e-test-{i}"
        alert_uuid = await conn.fetchval("""
            INSERT INTO superops.alerts (alert_id, message, severity, source, asset_id, client_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """, alert_id_str, messages[i], severities[i], 'e2e-test', asset_id, client_id,
            datetime.utcnow() - timedelta(minutes=30-i*5))
        alert_ids.append(alert_id_str)
        alert_uuids.append(alert_uuid)

    print_success(f"Created {len(alert_ids)} test alerts")
    return alert_ids, alert_uuids, client_id

async def create_ml_classifications(conn, alert_ids):
    """Insert ML classification data"""
    print_info("Creating ML classifications...")

    classifications = ['NOISE', 'ACTIONABLE', 'CRITICAL', 'ACTIONABLE']
    confidences = [0.95, 0.82, 0.98, 0.75]

    for i, alert_id in enumerate(alert_ids):
        await conn.execute("""
            INSERT INTO superops.ml_classifications
            (alert_id, classification, confidence, tier1_latency_ms, tier2_latency_ms, tier3_latency_ms, total_latency_ms)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, alert_id, classifications[i], confidences[i], 8.5, 45.2, 180.3, 234.0)

    print_success(f"Created ML classifications for {len(alert_ids)} alerts")

async def create_action_logs(conn, alert_ids, alert_uuids):
    """Insert action log entries"""
    print_info("Creating action logs...")

    actions = ['AUTO_SUPPRESS', 'ESCALATE', 'ESCALATE', 'REVIEW']
    reasons = [
        'Duplicate of alert 123, confidence 95%',
        'Critical severity - immediate attention required',
        'High priority - resource threshold exceeded',
        'Medium confidence - human review needed'
    ]

    for i, (alert_id, alert_uuid) in enumerate(zip(alert_ids, alert_uuids)):
        await conn.execute("""
            INSERT INTO audit.action_logs
            (alert_id, action, classification, confidence, reason, performed_by, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, alert_uuid, actions[i],  # Use UUID for audit.action_logs.alert_id
            await conn.fetchval("SELECT classification FROM superops.ml_classifications WHERE alert_id = $1", alert_id),  # Use VARCHAR for ml_classifications lookup
            await conn.fetchval("SELECT confidence FROM superops.ml_classifications WHERE alert_id = $1", alert_id),
            reasons[i], 'e2e-test',
            datetime.utcnow() - timedelta(minutes=25-i*5))

    print_success(f"Created action logs for {len(alert_ids)} alerts")

async def test_api_endpoints():
    """Test all REST API endpoints"""
    print_section("Testing REST API Endpoints")

    async with httpx.AsyncClient() as client:
        # Test /health
        print_info("Testing /health endpoint...")
        resp = await client.get(f"{API_BASE_URL}/health")
        assert resp.status_code == 200
        health = resp.json()
        assert health['status'] == 'healthy'
        assert health['redis_connected'] == True
        print_success(f"/health - Status: {health['status']}, Redis: Connected")

        # Test /api/alerts
        print_info("Testing /api/alerts endpoint...")
        resp = await client.get(f"{API_BASE_URL}/api/alerts?page_size=10")
        assert resp.status_code == 200
        alerts_data = resp.json()
        assert 'alerts' in alerts_data
        assert alerts_data['total_count'] >= 4  # At least our 4 test alerts
        print_success(f"/api/alerts - Found {alerts_data['total_count']} alerts")

        # Test /api/alerts with filters
        print_info("Testing /api/alerts with filters...")
        resp = await client.get(f"{API_BASE_URL}/api/alerts?status=AUTO_SUPPRESS&page_size=10")
        assert resp.status_code == 200
        filtered = resp.json()
        assert len(filtered['alerts']) >= 1  # At least 1 suppressed
        print_success(f"/api/alerts?status=AUTO_SUPPRESS - Found {len(filtered['alerts'])} suppressed alerts")

        # Test /api/metrics
        print_info("Testing /api/metrics endpoint...")
        resp = await client.get(f"{API_BASE_URL}/api/metrics")
        assert resp.status_code == 200
        metrics = resp.json()
        assert 'total_alerts' in metrics
        assert 'suppressed_alerts' in metrics
        assert 'suppression_rate' in metrics
        assert metrics['total_alerts'] >= 4
        print_success(f"/api/metrics - Total alerts: {metrics['total_alerts']}, Suppression rate: {metrics['suppression_rate']}%")

        # Test /api/clients
        print_info("Testing /api/clients endpoint...")
        resp = await client.get(f"{API_BASE_URL}/api/clients")
        assert resp.status_code == 200
        clients_data = resp.json()
        assert 'clients' in clients_data
        assert len(clients_data['clients']) >= 1
        print_success(f"/api/clients - Found {clients_data['total_count']} clients")

        # Test /api/clients/{client_id}
        client_id = clients_data['clients'][0]['id']
        print_info(f"Testing /api/clients/{client_id} endpoint...")
        resp = await client.get(f"{API_BASE_URL}/api/clients/{client_id}")
        assert resp.status_code == 200
        client_detail = resp.json()
        assert 'name' in client_detail
        assert 'total_alerts_24h' in client_detail
        print_success(f"/api/clients/{{id}} - Client: {client_detail['name']}, Alerts (24h): {client_detail['total_alerts_24h']}")

        # Test /api/audit-log
        print_info("Testing /api/audit-log endpoint...")
        resp = await client.get(f"{API_BASE_URL}/api/audit-log")
        assert resp.status_code == 200
        audit_data = resp.json()
        assert 'entries' in audit_data
        assert audit_data['total_count'] >= 4
        print_success(f"/api/audit-log - Found {audit_data['total_count']} audit entries")

        # Test /api/audit-log with filters
        print_info("Testing /api/audit-log with action filter...")
        resp = await client.get(f"{API_BASE_URL}/api/audit-log?action=ESCALATE")
        assert resp.status_code == 200
        filtered_audit = resp.json()
        assert len(filtered_audit['entries']) >= 2  # We created 2 ESCALATE actions
        print_success(f"/api/audit-log?action=ESCALATE - Found {len(filtered_audit['entries'])} escalations")

async def test_websocket_connection():
    """Test WebSocket connection and message reception"""
    print_section("Testing WebSocket Connection")

    print_info("Connecting to WebSocket...")
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            print_success("WebSocket connected successfully")

            # Wait for connection message
            print_info("Waiting for connection confirmation...")
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            assert data['type'] == 'connection_established'
            print_success(f"Received: {data['message']}")

            # Send ping
            print_info("Sending ping...")
            await websocket.send(json.dumps({'type': 'ping'}))

            # Wait for pong
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            assert data['type'] == 'pong'
            print_success("Received pong response")

    except asyncio.TimeoutError:
        print_error("WebSocket timeout")
        raise
    except Exception as e:
        print_error(f"WebSocket error: {e}")
        raise

async def test_database_connectivity():
    """Test database connection and data integrity"""
    print_section("Testing Database Connectivity")

    print_info("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    print_success("Database connected")

    # Check schemas exist
    print_info("Verifying database schemas...")
    schemas = await conn.fetch("SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('superops', 'customer', 'audit', 'knowledge_base')")
    assert len(schemas) == 4
    print_success(f"Found {len(schemas)} schemas")

    # Check tables exist
    print_info("Verifying critical tables...")
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'superops'
        AND table_name IN ('clients', 'assets', 'alerts', 'ml_classifications')
    """)
    assert len(tables) == 4
    print_success(f"Found {len(tables)} critical tables")

    await conn.close()

async def run_e2e_tests():
    """Run complete E2E test suite"""
    print(f"\n{BLUE}{'='*60}")
    print("  MSP BACKEND E2E TEST SUITE")
    print(f"{'='*60}{RESET}\n")

    conn = None
    try:
        # 1. Database connectivity test
        await test_database_connectivity()

        # 2. Setup test data
        print_section("Setting Up Test Data")
        conn = await asyncpg.connect(DATABASE_URL)

        # Cleanup first
        await cleanup_test_data(conn)

        # Create test data
        alert_ids, alert_uuids, client_id = await create_test_alerts(conn)
        await create_ml_classifications(conn, alert_ids)
        await create_action_logs(conn, alert_ids, alert_uuids)

        await conn.close()

        # 3. API endpoint tests
        await test_api_endpoints()

        # 4. WebSocket tests
        await test_websocket_connection()

        # 5. Cleanup
        print_section("Cleanup")
        conn = await asyncpg.connect(DATABASE_URL)
        await cleanup_test_data(conn)
        await conn.close()

        # Success summary
        print(f"\n{GREEN}{'='*60}")
        print("  ✓ ALL E2E TESTS PASSED")
        print(f"{'='*60}{RESET}\n")

        return True

    except AssertionError as e:
        print_error(f"Test assertion failed: {e}")
        return False
    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn and not conn.is_closed():
            await conn.close()

if __name__ == "__main__":
    result = asyncio.run(run_e2e_tests())
    exit(0 if result else 1)
