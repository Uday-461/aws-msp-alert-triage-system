"""
Root Cause Analysis API Routes
Provides endpoints for alert correlation and root cause identification
"""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from database import get_pool
from services.root_cause_analyzer import RootCauseAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/root-cause",
    tags=["root-cause"]
)

# Response models
class CorrelationFactors(BaseModel):
    time_score: float
    resource_score: float
    similarity_score: float

class RelatedAlert(BaseModel):
    alert_id: str
    alert_code: str
    message: str
    severity: str
    correlation_score: float
    is_root_cause: bool
    created_at: str
    correlation_factors: Optional[CorrelationFactors] = None

class AlertGroup(BaseModel):
    group_id: str
    root_cause_alert_id: str
    root_cause_alert_code: str
    root_cause_message: str
    root_cause_severity: str
    client_id: Optional[str]
    client_name: Optional[str]
    asset_id: Optional[str]
    category: Optional[str]
    time_window_start: str
    time_window_end: str
    alert_count: int
    confidence_score: float
    status: str
    created_at: str

class RelatedAlertsResponse(BaseModel):
    group_id: str
    total_alerts: int
    root_cause: RelatedAlert
    related_alerts: List[RelatedAlert]
    time_window: dict

class GroupListResponse(BaseModel):
    groups: List[AlertGroup]
    total: int
    page: int
    page_size: int

class AnalysisResponse(BaseModel):
    group_id: str
    is_new_group: bool
    correlation_score: float
    message: str


@router.get("/alerts/{alert_id}/related", response_model=RelatedAlertsResponse)
async def get_related_alerts(alert_id: str):
    """
    Get all alerts in the same correlation group as the specified alert.

    Returns:
    - group_id: UUID of the correlation group
    - total_alerts: Number of alerts in the group
    - root_cause: The identified root cause alert
    - related_alerts: All other alerts in the group
    - time_window: Start and end time of the correlation window
    """
    try:
        pool = await get_pool()
        analyzer = RootCauseAnalyzer(pool)

        result = await analyzer.get_related_alerts(alert_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No correlation group found for alert {alert_id}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting related alerts for {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups", response_model=GroupListResponse)
async def list_alert_groups(
    time_range: str = Query(default="24h", description="Time range: 1h, 24h, 7d, 30d"),
    client_id: Optional[str] = Query(default=None, description="Filter by client ID"),
    status: Optional[str] = Query(default="active", description="Filter by status: active, resolved, closed"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page")
):
    """
    List all alert correlation groups with pagination and filtering.

    Query Parameters:
    - time_range: Filter groups by creation time (1h, 24h, 7d, 30d)
    - client_id: Filter by specific client
    - status: Filter by group status (active, resolved, closed)
    - page: Page number for pagination
    - page_size: Number of items per page
    """
    try:
        pool = await get_pool()

        # Parse time range to hours
        time_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
        hours = time_map.get(time_range, 24)

        # Build query - FIXED: Use proper parameter binding for INTERVAL and convert types to strings
        query = """
            SELECT
                ag.group_id::TEXT,
                ag.root_cause_alert_id::TEXT,
                a.alert_id as root_cause_alert_code,
                a.message as root_cause_message,
                a.severity as root_cause_severity,
                ag.client_id::TEXT,
                c.client_name,
                ag.asset_id::TEXT,
                ag.category,
                ag.time_window_start::TEXT,
                ag.time_window_end::TEXT,
                ag.alert_count,
                ag.confidence_score,
                ag.status,
                ag.created_at::TEXT
            FROM superops.alert_groups ag
            LEFT JOIN superops.alerts a ON ag.root_cause_alert_id = a.id
            LEFT JOIN superops.clients c ON ag.client_id = c.id
            WHERE ag.created_at >= NOW() - INTERVAL '1 hour' * $1
        """
        params = [hours]

        if client_id:
            query += " AND ag.client_id = $%d" % (len(params) + 1)
            params.append(client_id)

        if status:
            query += " AND ag.status = $%d" % (len(params) + 1)
            params.append(status)

        # Get total count
        count_query = """
            SELECT COUNT(*)
            FROM superops.alert_groups ag
            WHERE ag.created_at >= NOW() - INTERVAL '1 hour' * $1
        """
        count_params = [hours]
        
        if client_id:
            count_query += " AND ag.client_id = $%d" % (len(count_params) + 1)
            count_params.append(client_id)

        if status:
            count_query += " AND ag.status = $%d" % (len(count_params) + 1)
            count_params.append(status)

        async with pool.acquire() as conn:
            total = await conn.fetchval(count_query, *count_params)

            # Add pagination
            query += f" ORDER BY ag.created_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
            params.extend([page_size, (page - 1) * page_size])

            rows = await conn.fetch(query, *params)

        groups = [dict(row) for row in rows]

        return {
            "groups": groups,
            "total": total or 0,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error listing alert groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{alert_id}", response_model=AnalysisResponse)
async def analyze_alert(alert_id: str):
    """
    Manually trigger root cause analysis for a specific alert.

    This will:
    1. Find potential correlation groups within the time window
    2. Calculate correlation scores for each group
    3. Add alert to group if score > threshold (0.7)
    4. Create new group if no matches found

    Returns:
    - group_id: UUID of the correlation group
    - is_new_group: Whether a new group was created
    - correlation_score: Score for best match (if joining existing group)
    - message: Summary of action taken
    """
    try:
        pool = await get_pool()
        analyzer = RootCauseAnalyzer(pool)

        result = await analyzer.analyze_alert(alert_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/groups/{group_id}/identify-root-cause")
async def identify_root_cause(group_id: str):
    """
    Re-identify the root cause for a correlation group.

    This analyzes all alerts in the group and selects the most likely
    root cause based on:
    - Time (earlier alerts score higher)
    - Severity (higher severity scores higher)
    - Connections (more related alerts scores higher)

    Returns:
    - root_cause_alert_id: UUID of the identified root cause
    - message: Summary of identification
    """
    try:
        pool = await get_pool()
        analyzer = RootCauseAnalyzer(pool)

        root_cause_id = await analyzer.identify_root_cause(group_id)

        if not root_cause_id:
            raise HTTPException(
                status_code=404,
                detail=f"Group {group_id} not found or has no members"
            )

        return {
            "root_cause_alert_id": root_cause_id,
            "message": f"Root cause identified and updated for group {group_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error identifying root cause for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{group_id}")
async def get_group_details(group_id: str):
    """
    Get detailed information about a specific correlation group.

    Returns:
    - Group metadata (time window, confidence, status)
    - Root cause alert details
    - All member alerts with correlation scores
    """
    try:
        pool = await get_pool()

        async with pool.acquire() as conn:
            # Get group details
            group = await conn.fetchrow("""
                SELECT * FROM superops.alert_groups_summary
                WHERE group_id = $1
            """, group_id)

            if not group:
                raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

            # Get all members
            members = await conn.fetch("""
                SELECT
                    agm.alert_id,
                    a.alert_id as alert_code,
                    a.message,
                    a.severity,
                    agm.correlation_score,
                    agm.is_root_cause,
                    agm.correlation_factors,
                    a.created_at
                FROM superops.alert_group_members agm
                JOIN superops.alerts a ON agm.alert_id = a.id
                WHERE agm.group_id = $1
                ORDER BY agm.is_root_cause DESC, agm.correlation_score DESC
            """, group_id)

        return {
            "group": dict(group),
            "members": [dict(m) for m in members]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting group details for {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/groups/{group_id}/status")
async def update_group_status(
    group_id: str,
    status: str = Query(..., description="New status: active, resolved, closed")
):
    """
    Update the status of a correlation group.

    Valid statuses:
    - active: Group is still being monitored
    - resolved: Root cause has been addressed
    - closed: Group is archived
    """
    valid_statuses = ["active", "resolved", "closed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    try:
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE superops.alert_groups
                SET status = $1, updated_at = NOW()
                WHERE group_id = $2
            """, status, group_id)

            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

        return {
            "group_id": group_id,
            "status": status,
            "message": f"Group status updated to {status}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating group status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_correlation_stats():
    """
    Get overall statistics about root cause analysis.

    Returns:
    - total_groups: Total number of correlation groups
    - active_groups: Number of active groups
    - avg_group_size: Average number of alerts per group
    - avg_confidence: Average correlation confidence score
    - groups_by_status: Breakdown by status
    """
    try:
        pool = await get_pool()

        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_groups,
                    COUNT(*) FILTER (WHERE status = 'active') as active_groups,
                    AVG(alert_count)::NUMERIC(10,2) as avg_group_size,
                    AVG(confidence_score)::NUMERIC(10,3) as avg_confidence
                FROM superops.alert_groups
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)

            by_status = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM superops.alert_groups
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY status
            """)

        return {
            **dict(stats),
            "groups_by_status": {row['status']: row['count'] for row in by_status}
        }

    except Exception as e:
        logger.error(f"Error getting correlation stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
