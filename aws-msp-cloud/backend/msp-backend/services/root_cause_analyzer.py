"""
Root Cause Analyzer Service
Correlates alerts and identifies root causes through multi-dimensional scoring
"""
import asyncpg
import logging
import math
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    """
    Analyzes alerts to identify correlations and root causes.

    Correlation scoring:
    - Time proximity: 0-0.3 (exponential decay within 5-minute windows)
    - Resource matching: 0-0.3 (0.15 for same client, 0.15 for same asset)
    - Message similarity: 0-0.4 (from Sentence-BERT similarity_score)

    Total correlation score: 0.0-1.0
    Grouping threshold: 0.7
    """

    # Scoring weights
    TIME_MAX_SCORE = 0.3
    RESOURCE_MAX_SCORE = 0.3
    SIMILARITY_MAX_SCORE = 0.4

    # Configuration
    TIME_WINDOW_SECONDS = 300  # 5 minutes
    GROUPING_THRESHOLD = 0.7

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize RootCauseAnalyzer with database connection pool.

        Args:
            db_pool: asyncpg connection pool
        """
        self.db_pool = db_pool
        logger.info("RootCauseAnalyzer initialized")

    async def analyze_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Find or create alert group for new alert.

        Process:
        1. Fetch alert details
        2. Find potential matching groups within time window
        3. Calculate correlation scores for each group
        4. If score >= threshold, add to best matching group
        5. Otherwise, create new group with this alert as root cause

        Args:
            alert_id: UUID of the alert to analyze

        Returns:
            Dict with group_id, is_new_group, correlation_score
            None if alert not found
        """
        async with self.db_pool.acquire() as conn:
            # Fetch alert details
            alert = await conn.fetchrow("""
                SELECT
                    a.id, a.alert_id, a.message, a.severity,
                    a.client_id, a.asset_id, a.created_at, a.alert_category
                FROM superops.alerts a
                WHERE a.id = $1
            """, alert_id)

            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return None

            logger.info(f"Analyzing alert {alert['alert_id']}: {alert['message'][:50]}")

            # Check if alert already in a group
            existing = await conn.fetchval("""
                SELECT group_id
                FROM superops.alert_group_members
                WHERE alert_id = $1
            """, alert_id)

            if existing:
                logger.info(f"Alert {alert_id} already in group {existing}")
                return {
                    "group_id": existing,
                    "is_new_group": False,
                    "correlation_score": 1.0,
                    "reason": "already_grouped"
                }

            # Find potential matching groups
            matching_groups = await self._find_matching_groups(
                alert['client_id'],
                alert['asset_id'],
                alert['created_at']
            )

            if not matching_groups:
                logger.info(f"No matching groups found, creating new group for alert {alert_id}")
                new_group = await self._create_new_group(alert)
                return {
                    "group_id": new_group['group_id'],
                    "is_new_group": True,
                    "correlation_score": 1.0,
                    "reason": "no_matches"
                }

            # Calculate correlation scores for each group
            best_group = None
            best_score = 0.0

            for group in matching_groups:
                score = await self._calculate_correlation(alert, group, conn)
                logger.debug(f"Group {group['group_id']}: correlation score {score:.3f}")

                if score > best_score:
                    best_score = score
                    best_group = group

            # Check if best score meets threshold
            if best_score >= self.GROUPING_THRESHOLD:
                logger.info(f"Adding alert {alert_id} to group {best_group['group_id']} (score: {best_score:.3f})")
                await self._add_to_group(best_group['group_id'], alert_id, best_score)
                return {
                    "group_id": best_group['group_id'],
                    "is_new_group": False,
                    "correlation_score": best_score,
                    "reason": "matched"
                }
            else:
                logger.info(f"Best score {best_score:.3f} below threshold, creating new group for alert {alert_id}")
                new_group = await self._create_new_group(alert)
                return {
                    "group_id": new_group['group_id'],
                    "is_new_group": True,
                    "correlation_score": 1.0,
                    "reason": "below_threshold"
                }

    async def _find_matching_groups(
        self,
        client_id: str,
        asset_id: Optional[str],
        timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """
        Find potential groups within time window.

        Looks for active groups where:
        - Time window overlaps with alert timestamp ± 5 minutes
        - Optionally filters by client or asset

        Args:
            client_id: Client UUID
            asset_id: Asset UUID (can be None)
            timestamp: Alert timestamp

        Returns:
            List of matching group records
        """
        window_start = timestamp - timedelta(seconds=self.TIME_WINDOW_SECONDS)
        window_end = timestamp + timedelta(seconds=self.TIME_WINDOW_SECONDS)

        async with self.db_pool.acquire() as conn:
            # Find groups with overlapping time windows
            # Prioritize same client/asset but don't require it
            groups = await conn.fetch("""
                SELECT
                    ag.group_id,
                    ag.root_cause_alert_id,
                    ag.client_id,
                    ag.asset_id,
                    ag.category,
                    ag.time_window_start,
                    ag.time_window_end,
                    ag.alert_count,
                    ag.confidence_score
                FROM superops.alert_groups ag
                WHERE ag.status = 'active'
                    AND ag.time_window_end >= $1
                    AND ag.time_window_start <= $2
                ORDER BY
                    CASE
                        WHEN ag.client_id = $3 THEN 1
                        ELSE 2
                    END,
                    CASE
                        WHEN ag.asset_id = $4 THEN 1
                        ELSE 2
                    END,
                    ag.updated_at DESC
                LIMIT 20
            """, window_start, window_end, client_id, asset_id)

            logger.debug(f"Found {len(groups)} potential matching groups")
            return [dict(g) for g in groups]

    async def _calculate_correlation(
        self,
        alert: Dict[str, Any],
        group: Dict[str, Any],
        conn: asyncpg.Connection
    ) -> float:
        """
        Calculate correlation score between alert and group.

        Components:
        1. Time proximity (0-0.3): Exponential decay based on time difference
        2. Resource matching (0-0.3): 0.15 if same client, 0.15 if same asset
        3. Message similarity (0-0.4): From Sentence-BERT similarity_score

        Args:
            alert: Alert record
            group: Group record
            conn: Database connection

        Returns:
            Correlation score (0.0-1.0)
        """
        scores = {
            "time_score": 0.0,
            "resource_score": 0.0,
            "similarity_score": 0.0
        }

        # 1. Time Proximity Score (0-0.3)
        # Get root cause alert timestamp
        root_alert = await conn.fetchrow("""
            SELECT created_at
            FROM superops.alerts
            WHERE id = $1
        """, group['root_cause_alert_id'])

        if root_alert:
            time_diff = abs((alert['created_at'] - root_alert['created_at']).total_seconds())
            # Exponential decay: score = max_score * e^(-λt)
            # λ = ln(100) / TIME_WINDOW to get ~1% at window boundary
            decay_factor = math.log(100) / self.TIME_WINDOW_SECONDS
            scores['time_score'] = self.TIME_MAX_SCORE * math.exp(-decay_factor * time_diff)

        # 2. Resource Matching Score (0-0.3)
        if alert['client_id'] == group['client_id']:
            scores['resource_score'] += 0.15

        if alert['asset_id'] and alert['asset_id'] == group['asset_id']:
            scores['resource_score'] += 0.15

        # 3. Message Similarity Score (0-0.4)
        # Get similarity score from ml_classifications
        # Compare against all alerts in the group
        similarity = await conn.fetchval("""
            SELECT COALESCE(MAX(ml.similarity_score), 0.0)
            FROM superops.alert_group_members agm
            JOIN superops.ml_classifications ml ON ml.alert_id = agm.alert_id::text
            WHERE agm.group_id = $1
                AND ml.similarity_score IS NOT NULL
        """, group['group_id'])

        if similarity and similarity > 0:
            # Scale similarity (0-1) to max score (0-0.4)
            scores['similarity_score'] = similarity * self.SIMILARITY_MAX_SCORE

        total_score = sum(scores.values())

        logger.debug(
            f"Correlation scores - Time: {scores['time_score']:.3f}, "
            f"Resource: {scores['resource_score']:.3f}, "
            f"Similarity: {scores['similarity_score']:.3f}, "
            f"Total: {total_score:.3f}"
        )

        return total_score

    async def _add_to_group(
        self,
        group_id: str,
        alert_id: str,
        correlation_score: float
    ) -> None:
        """
        Add alert to existing group.

        Updates:
        - Inserts into alert_group_members
        - Updates group time window if needed
        - Stores correlation factors as JSONB

        Args:
            group_id: Group UUID
            alert_id: Alert UUID
            correlation_score: Calculated correlation score
        """
        async with self.db_pool.acquire() as conn:
            # Get detailed correlation factors for storage
            alert = await conn.fetchrow("""
                SELECT id, created_at, client_id, asset_id
                FROM superops.alerts
                WHERE id = $1
            """, alert_id)

            group = await conn.fetchrow("""
                SELECT group_id, root_cause_alert_id, time_window_start, time_window_end
                FROM superops.alert_groups
                WHERE group_id = $1
            """, group_id)

            # Calculate individual scores for storage
            root_alert = await conn.fetchrow("""
                SELECT created_at
                FROM superops.alerts
                WHERE id = $1
            """, group['root_cause_alert_id'])

            time_diff = abs((alert['created_at'] - root_alert['created_at']).total_seconds())
            decay_factor = math.log(100) / self.TIME_WINDOW_SECONDS
            time_score = self.TIME_MAX_SCORE * math.exp(-decay_factor * time_diff)

            # Resource score
            resource_score = 0.0
            if alert['client_id']:
                resource_score += 0.15
            if alert['asset_id']:
                resource_score += 0.15

            # Similarity score (derive from total)
            similarity_score = correlation_score - time_score - resource_score

            correlation_factors = {
                "time_score": round(time_score, 4),
                "resource_score": round(resource_score, 4),
                "similarity_score": round(max(0, similarity_score), 4),
                "time_diff_seconds": round(time_diff, 2)
            }

            # Insert into alert_group_members
            await conn.execute("""
                INSERT INTO superops.alert_group_members
                    (group_id, alert_id, is_root_cause, correlation_score, correlation_factors)
                VALUES ($1, $2, false, $3, $4)
                ON CONFLICT (group_id, alert_id) DO NOTHING
            """, group_id, alert_id, correlation_score, json.dumps(correlation_factors))

            # Update group time window if needed
            await conn.execute("""
                UPDATE superops.alert_groups
                SET
                    time_window_start = LEAST(time_window_start, $2),
                    time_window_end = GREATEST(time_window_end, $2)
                WHERE group_id = $1
            """, group_id, alert['created_at'])

            logger.info(f"Added alert {alert_id} to group {group_id} with score {correlation_score:.3f}")

    async def _create_new_group(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new alert group with alert as root cause.

        Initializes:
        - New group record
        - First member (this alert as root cause)
        - Time window centered on alert timestamp

        Args:
            alert: Alert record

        Returns:
            New group record with group_id
        """
        async with self.db_pool.acquire() as conn:
            # Create time window ± 5 minutes from alert time
            window_start = alert['created_at'] - timedelta(seconds=self.TIME_WINDOW_SECONDS)
            window_end = alert['created_at'] + timedelta(seconds=self.TIME_WINDOW_SECONDS)

            # Create new group
            group = await conn.fetchrow("""
                INSERT INTO superops.alert_groups
                    (root_cause_alert_id, client_id, asset_id, category,
                     time_window_start, time_window_end, alert_count,
                     confidence_score, status)
                VALUES ($1, $2, $3, $4, $5, $6, 1, 1.0, 'active')
                RETURNING group_id, root_cause_alert_id, client_id, asset_id,
                          time_window_start, time_window_end
            """,
                alert['id'],
                alert['client_id'],
                alert['asset_id'],
                alert['alert_category'],
                window_start,
                window_end
            )

            # Add alert as root cause member
            correlation_factors = {
                "time_score": self.TIME_MAX_SCORE,
                "resource_score": self.RESOURCE_MAX_SCORE,
                "similarity_score": self.SIMILARITY_MAX_SCORE,
                "time_diff_seconds": 0.0
            }

            await conn.execute("""
                INSERT INTO superops.alert_group_members
                    (group_id, alert_id, is_root_cause, correlation_score, correlation_factors)
                VALUES ($1, $2, true, 1.0, $3)
            """, group['group_id'], alert['id'], json.dumps(correlation_factors))

            logger.info(f"Created new group {group['group_id']} with root cause alert {alert['id']}")

            return dict(group)

    async def identify_root_cause(self, group_id: str) -> Optional[str]:
        """
        Identify most likely root cause in group.

        Selection criteria (in order):
        1. Earliest timestamp
        2. Highest severity (CRITICAL > HIGH > MEDIUM > LOW)
        3. Most connections (highest number of correlated alerts)

        Args:
            group_id: Group UUID

        Returns:
            Alert ID of identified root cause, or None if group not found
        """
        async with self.db_pool.acquire() as conn:
            # Get all alerts in group with details
            alerts = await conn.fetch("""
                SELECT
                    agm.alert_id,
                    a.created_at,
                    a.severity,
                    agm.is_root_cause,
                    COUNT(*) OVER (PARTITION BY agm.group_id) as total_in_group
                FROM superops.alert_group_members agm
                JOIN superops.alerts a ON a.id = agm.alert_id
                WHERE agm.group_id = $1
                ORDER BY
                    a.created_at ASC,
                    CASE a.severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        WHEN 'LOW' THEN 4
                        ELSE 5
                    END,
                    agm.correlation_score DESC
                LIMIT 1
            """, group_id)

            if not alerts:
                logger.warning(f"Group {group_id} has no alerts")
                return None

            root_cause_id = alerts[0]['alert_id']

            # Update group if root cause changed
            await conn.execute("""
                UPDATE superops.alert_groups
                SET root_cause_alert_id = $2
                WHERE group_id = $1 AND root_cause_alert_id != $2
            """, group_id, root_cause_id)

            # Update is_root_cause flags
            await conn.execute("""
                UPDATE superops.alert_group_members
                SET is_root_cause = (alert_id = $2)
                WHERE group_id = $1
            """, group_id, root_cause_id)

            logger.info(f"Identified root cause for group {group_id}: {root_cause_id}")

            return str(root_cause_id)

    async def get_related_alerts(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all alerts in same group as given alert.

        Uses the PostgreSQL function superops.get_related_alerts() which returns:
        - group_id
        - alert_id
        - alert_code
        - message
        - severity
        - correlation_score
        - is_root_cause
        - created_at

        Args:
            alert_id: Alert UUID

        Returns:
            Dict with group_id, root_cause, and list of related alerts
            None if alert not in any group
        """
        async with self.db_pool.acquire() as conn:
            # Use the database function
            related = await conn.fetch("""
                SELECT * FROM superops.get_related_alerts($1)
            """, alert_id)

            if not related:
                logger.info(f"Alert {alert_id} is not in any group")
                return None

            group_id = related[0]['group_id']

            # Get group time window
            group_info = await conn.fetchrow("""
                SELECT time_window_start, time_window_end
                FROM superops.alert_groups
                WHERE group_id = $1
            """, group_id)

            # Find root cause and convert types
            root_cause_raw = next(
                (r for r in related if r['is_root_cause']),
                None
            )

            # Convert root_cause types to match Pydantic model
            root_cause = {
                "alert_id": str(root_cause_raw['alert_id']),
                "alert_code": root_cause_raw['alert_code'],
                "message": root_cause_raw['message'],
                "severity": root_cause_raw['severity'],
                "correlation_score": float(root_cause_raw['correlation_score']) if root_cause_raw['correlation_score'] else 0.0,
                "is_root_cause": root_cause_raw['is_root_cause'],
                "created_at": root_cause_raw['created_at'].isoformat()
            } if root_cause_raw else None

            # Build response
            result = {
                "group_id": str(group_id),
                "total_alerts": len(related),
                "root_cause": root_cause,
                "related_alerts": [
                    {
                        "alert_id": str(r['alert_id']),
                        "alert_code": r['alert_code'],
                        "message": r['message'],
                        "severity": r['severity'],
                        "correlation_score": float(r['correlation_score']) if r['correlation_score'] else 0.0,
                        "is_root_cause": r['is_root_cause'],
                        "created_at": r['created_at'].isoformat()
                    }
                    for r in related
                    if not r['is_root_cause']  # Exclude root cause from related list
                ],
                "time_window": {
                    "start": group_info['time_window_start'].isoformat() if group_info else None,
                    "end": group_info['time_window_end'].isoformat() if group_info else None
                }
            }

            logger.info(
                f"Found {result['total_alerts']} related alerts for {alert_id} "
                f"in group {group_id}"
            )

            return result


# Module-level function for easy import
async def create_root_cause_analyzer(db_pool: asyncpg.Pool) -> RootCauseAnalyzer:
    """
    Factory function to create RootCauseAnalyzer instance.

    Args:
        db_pool: asyncpg connection pool

    Returns:
        Initialized RootCauseAnalyzer
    """
    return RootCauseAnalyzer(db_pool)
