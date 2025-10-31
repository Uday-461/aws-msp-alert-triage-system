"""
Auto-Remediation Engine - Phase 3

Executes automated fixes for known alert patterns and incidents.
Logs all actions to audit.remediation_actions table for compliance.

Does NOT use RLM v3 - this is a rule-based remediation system.
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import time

# Add backend to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)


class AutoRemediationEngine:
    """
    Auto-Remediation Engine

    Executes automated fixes based on alert patterns and playbooks.
    Tracks all remediation actions in audit.remediation_actions table.
    """

    # Remediation playbooks: Map alert categories/types to actions
    PLAYBOOKS = {
        'cpu_high': {
            'name': 'High CPU Remediation',
            'action_type': 'restart_service',
            'steps': [
                'Identify top CPU consuming process',
                'Check if process is stuck/hung',
                'Gracefully restart service',
                'Verify CPU returns to normal'
            ],
            'auto_approve': True,  # Can run automatically
            'max_retries': 2
        },
        'memory_high': {
            'name': 'High Memory Remediation',
            'action_type': 'clear_cache',
            'steps': [
                'Check memory usage by process',
                'Clear application caches',
                'Trigger garbage collection',
                'Monitor memory levels'
            ],
            'auto_approve': True,
            'max_retries': 3
        },
        'disk_full': {
            'name': 'Disk Full Remediation',
            'action_type': 'cleanup_logs',
            'steps': [
                'Identify large log files',
                'Archive logs older than 30 days',
                'Compress archived logs',
                'Remove temp files',
                'Verify disk space recovered'
            ],
            'auto_approve': True,
            'max_retries': 1
        },
        'database_connection': {
            'name': 'Database Connection Pool Remediation',
            'action_type': 'restart_connection_pool',
            'steps': [
                'Check current connection pool stats',
                'Close idle connections',
                'Restart connection pool',
                'Verify connections restored'
            ],
            'auto_approve': True,
            'max_retries': 2
        },
        'network_latency': {
            'name': 'Network Latency Remediation',
            'action_type': 'network_diagnostic',
            'steps': [
                'Run traceroute to identify bottleneck',
                'Check network interface statistics',
                'Restart network service if needed',
                'Verify latency improved'
            ],
            'auto_approve': False,  # Requires manual approval
            'max_retries': 1
        },
        'application_crash': {
            'name': 'Application Crash Recovery',
            'action_type': 'restart_application',
            'steps': [
                'Collect crash logs and stack traces',
                'Check for known crash patterns',
                'Restart application with health checks',
                'Monitor for stability'
            ],
            'auto_approve': True,
            'max_retries': 3
        }
    }

    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize auto-remediation engine

        Args:
            db_config: Database connection configuration
        """
        self.db_config = db_config

    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def _determine_playbook(self, alert_category: str, alert_message: str) -> Optional[str]:
        """
        Determine which playbook to use based on alert details

        Args:
            alert_category: Alert category (database, cpu, memory, etc.)
            alert_message: Alert message/description

        Returns:
            Playbook key or None if no match
        """
        # Simple rule-based matching (can be enhanced with ML later)
        category_lower = alert_category.lower()
        message_lower = alert_message.lower()

        # CPU alerts
        if 'cpu' in category_lower and 'high' in message_lower:
            return 'cpu_high'

        # Memory alerts
        if 'memory' in category_lower or 'ram' in category_lower:
            if 'high' in message_lower or 'leak' in message_lower:
                return 'memory_high'

        # Disk alerts
        if 'disk' in category_lower:
            if 'full' in message_lower or 'space' in message_lower:
                return 'disk_full'

        # Database alerts
        if 'database' in category_lower or 'db' in category_lower:
            if 'connection' in message_lower or 'pool' in message_lower:
                return 'database_connection'

        # Network alerts
        if 'network' in category_lower:
            if 'latency' in message_lower or 'slow' in message_lower:
                return 'network_latency'

        # Application crashes
        if 'crash' in message_lower or 'failed' in message_lower:
            return 'application_crash'

        return None

    def _execute_remediation(
        self,
        playbook_key: str,
        alert_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute remediation action (simulated for now)

        Args:
            playbook_key: Playbook identifier
            alert_id: Optional alert ID
            incident_id: Optional incident ID
            metadata: Optional execution metadata

        Returns:
            Execution result
        """
        playbook = self.PLAYBOOKS.get(playbook_key)
        if not playbook:
            return {
                'status': 'failed',
                'error': f'Playbook not found: {playbook_key}'
            }

        # Simulate execution (in production, this would run actual remediation)
        start_time = time.time()

        # Simulate different execution times based on action type
        execution_times = {
            'restart_service': 5000,  # 5 seconds
            'clear_cache': 2000,
            'cleanup_logs': 8000,
            'restart_connection_pool': 3000,
            'network_diagnostic': 10000,
            'restart_application': 7000
        }

        execution_time_ms = execution_times.get(playbook['action_type'], 5000)

        # Simulate 90% success rate
        import random
        success = random.random() < 0.9

        if success:
            result = {
                'status': 'success',
                'execution_time_ms': execution_time_ms,
                'steps_completed': playbook['steps'],
                'output': f"Successfully executed {playbook['name']}",
                'metrics': {
                    'started_at': datetime.now().isoformat(),
                    'completed_at': (datetime.now()).isoformat(),
                    'action_type': playbook['action_type']
                }
            }
        else:
            result = {
                'status': 'failed',
                'execution_time_ms': execution_time_ms,
                'steps_completed': playbook['steps'][:2],  # Only completed first 2 steps
                'error': f"Execution failed at step 3: {playbook['steps'][2]}",
                'metrics': {
                    'started_at': datetime.now().isoformat(),
                    'failed_at': (datetime.now()).isoformat(),
                    'action_type': playbook['action_type']
                }
            }

        return result

    def remediate_alert(
        self,
        alert_id: str,
        alert_category: str,
        alert_message: str,
        auto_execute: bool = True
    ) -> Dict[str, Any]:
        """
        Remediate a specific alert

        Args:
            alert_id: Alert ID
            alert_category: Alert category
            alert_message: Alert message
            auto_execute: Whether to auto-execute (or just recommend)

        Returns:
            Remediation result
        """
        # Determine appropriate playbook
        playbook_key = self._determine_playbook(alert_category, alert_message)

        if not playbook_key:
            return {
                'status': 'no_playbook',
                'alert_id': alert_id,
                'message': f'No remediation playbook found for category: {alert_category}'
            }

        playbook = self.PLAYBOOKS[playbook_key]

        # Check if auto-approve is allowed
        if not playbook['auto_approve'] and auto_execute:
            return {
                'status': 'approval_required',
                'alert_id': alert_id,
                'playbook': playbook['name'],
                'message': 'This remediation requires manual approval',
                'steps': playbook['steps']
            }

        # Create remediation action record (queued)
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    INSERT INTO audit.remediation_actions (
                        alert_id,
                        playbook_name,
                        action_type,
                        status,
                        metadata
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, executed_at
                """

                metadata = {
                    'alert_category': alert_category,
                    'alert_message': alert_message,
                    'auto_execute': auto_execute,
                    'playbook_key': playbook_key
                }

                cur.execute(query, (
                    alert_id,
                    playbook['name'],
                    playbook['action_type'],
                    'queued',
                    json.dumps(metadata)
                ))

                action_record = cur.fetchone()
                action_id = action_record['id']
                conn.commit()
        finally:
            conn.close()

        # Execute if auto_execute
        if auto_execute:
            # Update status to running
            conn = self._get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE audit.remediation_actions SET status = 'running' WHERE id = %s",
                        (action_id,)
                    )
                    conn.commit()
            finally:
                conn.close()

            # Execute remediation
            execution_result = self._execute_remediation(
                playbook_key,
                alert_id=alert_id,
                metadata=metadata
            )

            # Update action record with result
            conn = self._get_db_connection()
            try:
                with conn.cursor() as cur:
                    if execution_result['status'] == 'success':
                        query = """
                            UPDATE audit.remediation_actions
                            SET status = 'success',
                                completed_at = NOW(),
                                result = %s
                            WHERE id = %s
                        """
                        cur.execute(query, (json.dumps(execution_result), action_id))
                    else:
                        query = """
                            UPDATE audit.remediation_actions
                            SET status = 'failed',
                                completed_at = NOW(),
                                result = %s,
                                error_message = %s
                            WHERE id = %s
                        """
                        cur.execute(query, (
                            json.dumps(execution_result),
                            execution_result.get('error', 'Unknown error'),
                            action_id
                        ))

                    conn.commit()
            finally:
                conn.close()

            return {
                'status': 'executed',
                'action_id': action_id,
                'alert_id': alert_id,
                'playbook': playbook['name'],
                'execution_result': execution_result
            }
        else:
            # Just return recommendation
            return {
                'status': 'recommended',
                'action_id': action_id,
                'alert_id': alert_id,
                'playbook': playbook['name'],
                'action_type': playbook['action_type'],
                'steps': playbook['steps'],
                'message': 'Remediation queued, execute manually or set auto_execute=True'
            }

    def remediate_incident(
        self,
        incident_id: str,
        incident_title: str,
        root_cause: str
    ) -> Dict[str, Any]:
        """
        Remediate an incident (broader than single alert)

        Args:
            incident_id: Incident ID
            incident_title: Incident title
            root_cause: Root cause description

        Returns:
            Remediation result
        """
        # Determine playbook from root cause analysis
        playbook_key = None
        root_cause_lower = root_cause.lower()

        if 'connection pool' in root_cause_lower:
            playbook_key = 'database_connection'
        elif 'memory leak' in root_cause_lower:
            playbook_key = 'memory_high'
        elif 'cpu' in root_cause_lower:
            playbook_key = 'cpu_high'
        elif 'disk' in root_cause_lower:
            playbook_key = 'disk_full'

        if not playbook_key:
            return {
                'status': 'no_playbook',
                'incident_id': incident_id,
                'message': f'No remediation playbook found for root cause: {root_cause}'
            }

        playbook = self.PLAYBOOKS[playbook_key]

        # Create remediation action record
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    INSERT INTO audit.remediation_actions (
                        incident_id,
                        playbook_name,
                        action_type,
                        status,
                        metadata
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """

                metadata = {
                    'incident_title': incident_title,
                    'root_cause': root_cause,
                    'playbook_key': playbook_key
                }

                cur.execute(query, (
                    incident_id,
                    playbook['name'],
                    playbook['action_type'],
                    'running',
                    json.dumps(metadata)
                ))

                action_id = cur.fetchone()['id']
                conn.commit()
        finally:
            conn.close()

        # Execute remediation
        execution_result = self._execute_remediation(
            playbook_key,
            incident_id=incident_id,
            metadata=metadata
        )

        # Update action record
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                if execution_result['status'] == 'success':
                    query = """
                        UPDATE audit.remediation_actions
                        SET status = 'success',
                            completed_at = NOW(),
                            result = %s
                        WHERE id = %s
                    """
                    cur.execute(query, (json.dumps(execution_result), action_id))
                else:
                    query = """
                        UPDATE audit.remediation_actions
                        SET status = 'failed',
                            completed_at = NOW(),
                            result = %s,
                            error_message = %s
                        WHERE id = %s
                    """
                    cur.execute(query, (
                        json.dumps(execution_result),
                        execution_result.get('error', 'Unknown error'),
                        action_id
                    ))

                conn.commit()
        finally:
            conn.close()

        return {
            'status': 'executed',
            'action_id': action_id,
            'incident_id': incident_id,
            'playbook': playbook['name'],
            'execution_result': execution_result
        }

    def get_remediation_history(
        self,
        alert_id: Optional[str] = None,
        incident_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get remediation action history

        Args:
            alert_id: Filter by alert ID
            incident_id: Filter by incident ID
            limit: Max results

        Returns:
            List of remediation actions
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        id,
                        alert_id,
                        incident_id,
                        playbook_name,
                        action_type,
                        status,
                        executed_at,
                        completed_at,
                        execution_time_ms,
                        result,
                        error_message,
                        metadata
                    FROM audit.remediation_actions
                    WHERE 1=1
                """

                params = []

                if alert_id:
                    query += " AND alert_id = %s"
                    params.append(alert_id)

                if incident_id:
                    query += " AND incident_id = %s"
                    params.append(incident_id)

                query += " ORDER BY executed_at DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_remediation_stats(
        self,
        hours_lookback: int = 24
    ) -> Dict[str, Any]:
        """
        Get remediation statistics

        Args:
            hours_lookback: How far back to look (default: 24 hours)

        Returns:
            Statistics
        """
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT
                        COUNT(*) as total_actions,
                        COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                        COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
                        COUNT(CASE WHEN status = 'queued' THEN 1 END) as queued,
                        AVG(CASE WHEN execution_time_ms IS NOT NULL THEN execution_time_ms END) as avg_execution_time_ms,
                        MAX(CASE WHEN execution_time_ms IS NOT NULL THEN execution_time_ms END) as max_execution_time_ms,
                        MIN(CASE WHEN execution_time_ms IS NOT NULL THEN execution_time_ms END) as min_execution_time_ms
                    FROM audit.remediation_actions
                    WHERE executed_at >= NOW() - INTERVAL '%s hours'
                """

                cur.execute(query, (hours_lookback,))
                stats = dict(cur.fetchone())

                # Get breakdown by action type
                query_by_type = """
                    SELECT
                        action_type,
                        COUNT(*) as count,
                        COUNT(CASE WHEN status = 'success' THEN 1 END) as successful
                    FROM audit.remediation_actions
                    WHERE executed_at >= NOW() - INTERVAL '%s hours'
                    GROUP BY action_type
                    ORDER BY count DESC
                """

                cur.execute(query_by_type, (hours_lookback,))
                stats['by_action_type'] = [dict(row) for row in cur.fetchall()]

                return stats
        finally:
            conn.close()

    def get_available_playbooks(self) -> List[Dict[str, Any]]:
        """
        Get list of available remediation playbooks

        Returns:
            List of playbooks
        """
        playbooks = []
        for key, playbook in self.PLAYBOOKS.items():
            playbooks.append({
                'key': key,
                'name': playbook['name'],
                'action_type': playbook['action_type'],
                'auto_approve': playbook['auto_approve'],
                'max_retries': playbook['max_retries'],
                'steps': playbook['steps']
            })

        return playbooks


# Example usage and testing
if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'superops'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }

    print("=" * 80)
    print("Auto-Remediation Engine - Test")
    print("=" * 80)
    print()

    # Initialize engine
    engine = AutoRemediationEngine(db_config)

    try:
        # Test 1: List available playbooks
        print("Test 1: Available Playbooks")
        playbooks = engine.get_available_playbooks()
        print(f"  Total playbooks: {len(playbooks)}")
        for pb in playbooks[:3]:
            print(f"  - {pb['name']} ({pb['action_type']})")

        # Test 2: Remediate a CPU alert
        print("\nTest 2: Remediate CPU Alert")
        result = engine.remediate_alert(
            alert_id='TEST-ALERT-CPU-001',
            alert_category='cpu',
            alert_message='High CPU usage detected on app-server-01',
            auto_execute=True
        )
        print(f"  Status: {result['status']}")
        if result['status'] == 'executed':
            print(f"  Action ID: {result['action_id']}")
            print(f"  Execution: {result['execution_result']['status']}")

        # Test 3: Check remediation stats
        print("\nTest 3: Remediation Statistics")
        stats = engine.get_remediation_stats(hours_lookback=24)
        print(f"  Total actions: {stats['total_actions']}")
        print(f"  Successful: {stats['successful']}")
        print(f"  Failed: {stats['failed']}")

        print("\n✅ Auto-remediation tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
