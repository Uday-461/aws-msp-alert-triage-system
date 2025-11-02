"""
Alert Lifecycle Management Service
Manages alert state transitions with validation and audit trail
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
import json
import logging
from asyncpg import Pool

logger = logging.getLogger(__name__)


class AlertStatus(str, Enum):
    """Valid alert lifecycle states"""
    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class AlertLifecycle:
    """
    Manages alert state transitions with validation and complete audit trail.

    Features:
    - State machine with validated transitions
    - Complete lifecycle history tracking
    - Assignment tracking
    - Transition duration metrics
    - Metadata storage for additional context
    """

    # Valid state transitions (directed graph)
    VALID_TRANSITIONS = {
        AlertStatus.NEW: [AlertStatus.INVESTIGATING],
        AlertStatus.INVESTIGATING: [AlertStatus.RESOLVED, AlertStatus.REOPENED],
        AlertStatus.RESOLVED: [AlertStatus.CLOSED, AlertStatus.REOPENED],
        AlertStatus.CLOSED: [AlertStatus.REOPENED],
        AlertStatus.REOPENED: [AlertStatus.INVESTIGATING]
    }

    def __init__(self, db_pool: Pool):
        """
        Initialize lifecycle manager with database connection pool.

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db = db_pool

    async def transition(
        self,
        alert_id: str,
        new_status: AlertStatus,
        assigned_to: Optional[str] = None,
        notes: Optional[str] = None,
        changed_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transition alert to new status with validation.

        Args:
            alert_id: UUID of the alert
            new_status: Target status to transition to
            assigned_to: Optional user assignment
            notes: Optional transition notes
            changed_by: User/system performing the transition
            metadata: Additional metadata for the transition

        Returns:
            Dict with transition details including old/new status and duration

        Raises:
            ValueError: If transition is invalid based on state machine
        """
        # Get current status
        current = await self.get_current_status(alert_id)
        current_status = AlertStatus(current['status']) if current else AlertStatus.NEW

        # Validate transition
        valid_next_states = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next_states:
            raise ValueError(
                f"Invalid transition from {current_status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid_next_states]}"
            )

        # Calculate duration since last transition
        duration_ms = None
        if current and current.get('transitioned_at'):
            # Handle timezone-aware datetime
            last_transition = current['transitioned_at']
            if last_transition.tzinfo:
                last_transition = last_transition.replace(tzinfo=None)
            duration = datetime.now() - last_transition
            duration_ms = int(duration.total_seconds() * 1000)

        # Prepare metadata
        meta = metadata or {}
        if notes:
            meta['notes'] = notes
        meta['changed_at'] = datetime.now().isoformat()

        # Record transition in database
        async with self.db.acquire() as conn:
            # Insert lifecycle record
            await conn.execute("""
                INSERT INTO superops.alert_lifecycle
                (alert_id, state, previous_state, assigned_to, transitioned_by,
                 transitioned_at, transition_duration_ms, metadata)
                VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7)
            """,
                alert_id,
                new_status.value,
                current_status.value if current else None,
                assigned_to,
                changed_by,
                duration_ms,
                json.dumps(meta) if meta else None
            )

            # Update alerts table status
            await conn.execute("""
                UPDATE superops.alerts
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, new_status.value, alert_id)

        logger.info(
            f"Alert {alert_id} transitioned: {current_status.value} → {new_status.value} "
            f"by {changed_by} (duration: {duration_ms}ms)"
        )

        return {
            "alert_id": alert_id,
            "old_status": current_status.value if current else None,
            "new_status": new_status.value,
            "changed_by": changed_by,
            "duration_ms": duration_ms,
            "assigned_to": assigned_to,
            "timestamp": datetime.now().isoformat()
        }

    async def get_history(self, alert_id: str) -> List[Dict[str, Any]]:
        """
        Get complete lifecycle history for an alert.

        Args:
            alert_id: UUID of the alert

        Returns:
            List of lifecycle transitions ordered chronologically
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id,
                    alert_id,
                    state,
                    previous_state,
                    assigned_to,
                    transitioned_by,
                    transitioned_at,
                    transition_duration_ms,
                    metadata
                FROM superops.alert_lifecycle
                WHERE alert_id = $1
                ORDER BY transitioned_at ASC
            """, alert_id)

        history = []
        for r in rows:
            record = dict(r)
            # Parse metadata JSON if present
            if record.get('metadata'):
                try:
                    record['metadata'] = json.loads(record['metadata']) if isinstance(record['metadata'], str) else record['metadata']
                except (json.JSONDecodeError, TypeError):
                    pass
            history.append(record)

        return history

    async def get_current_status(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status for an alert using the view.

        Args:
            alert_id: UUID of the alert

        Returns:
            Dict with current status or None if no lifecycle records exist
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM superops.alert_current_status
                WHERE alert_id = $1
            """, alert_id)

        if row:
            result = dict(row)
            # Parse metadata if present
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                except (json.JSONDecodeError, TypeError):
                    pass
            return result
        return None

    async def assign_to_user(
        self,
        alert_id: str,
        assignee: str,
        changed_by: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign alert to user without changing status.
        Creates a lifecycle record with same state but new assignment.

        Args:
            alert_id: UUID of the alert
            assignee: Username to assign to
            changed_by: User performing the assignment
            notes: Optional assignment notes

        Returns:
            Dict with assignment details
        """
        current = await self.get_current_status(alert_id)
        current_status = current['status'] if current else 'new'

        # Prepare metadata
        meta = {"assignment_change": True}
        if notes:
            meta['notes'] = notes
        meta['changed_at'] = datetime.now().isoformat()

        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO superops.alert_lifecycle
                (alert_id, state, previous_state, assigned_to, transitioned_by,
                 transitioned_at, metadata)
                VALUES ($1, $2, $2, $3, $4, NOW(), $5)
            """,
                alert_id,
                current_status,
                assignee,
                changed_by,
                json.dumps(meta)
            )

        logger.info(f"Alert {alert_id} assigned to {assignee} by {changed_by}")

        return {
            "alert_id": alert_id,
            "assigned_to": assignee,
            "changed_by": changed_by,
            "status": current_status,
            "timestamp": datetime.now().isoformat()
        }

    async def get_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get lifecycle metrics for analytics.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dict with various metrics (avg duration, state distribution, etc.)
        """
        async with self.db.acquire() as conn:
            # Build query with optional date filters
            date_filter = ""
            params = []
            if start_date:
                date_filter += " AND transitioned_at >= $1"
                params.append(start_date)
            if end_date:
                idx = len(params) + 1
                date_filter += f" AND transitioned_at <= ${idx}"
                params.append(end_date)

            # Get state distribution
            state_dist = await conn.fetch(f"""
                SELECT state, COUNT(*) as count
                FROM superops.alert_lifecycle
                WHERE 1=1 {date_filter}
                GROUP BY state
                ORDER BY count DESC
            """, *params)

            # Get average transition durations by state
            avg_durations = await conn.fetch(f"""
                SELECT
                    previous_state,
                    state,
                    AVG(transition_duration_ms) as avg_duration_ms,
                    COUNT(*) as transition_count
                FROM superops.alert_lifecycle
                WHERE transition_duration_ms IS NOT NULL {date_filter}
                GROUP BY previous_state, state
                ORDER BY avg_duration_ms DESC
            """, *params)

            # Get total transition count
            total = await conn.fetchval(f"""
                SELECT COUNT(*) FROM superops.alert_lifecycle
                WHERE 1=1 {date_filter}
            """, *params)

        return {
            "total_transitions": total,
            "state_distribution": [dict(r) for r in state_dist],
            "average_durations": [dict(r) for r in avg_durations],
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }

    async def bulk_update_status(
        self,
        alert_ids: List[str],
        new_status: AlertStatus,
        changed_by: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bulk update status for multiple alerts.

        Args:
            alert_ids: List of alert UUIDs
            new_status: Target status
            changed_by: User performing the update
            notes: Optional notes for all transitions

        Returns:
            Dict with success/failure counts
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(alert_ids)
        }

        for alert_id in alert_ids:
            try:
                result = await self.transition(
                    alert_id=alert_id,
                    new_status=new_status,
                    changed_by=changed_by,
                    notes=notes
                )
                results["successful"].append(result)
            except Exception as e:
                results["failed"].append({
                    "alert_id": alert_id,
                    "error": str(e)
                })
                logger.error(f"Failed to transition alert {alert_id}: {e}")

        return results
