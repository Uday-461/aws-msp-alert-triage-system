"""
Alert management API routes
GET /api/alerts - List alerts with filtering
GET /api/alerts/{alert_id} - Get alert details
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# Response models
class AlertResponse(BaseModel):
    id: str
    alert_id: str
    client_id: Optional[str]
    client_name: Optional[str]
    asset_id: Optional[str]
    asset_name: Optional[str]
    message: str
    severity: str
    source: Optional[str]
    created_at: datetime
    status: str
    ml_classification: Optional[str]
    ml_confidence: Optional[float]
    ml_action: Optional[str]

class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total_count: int
    page: int
    page_size: int

@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status: suppressed, escalated, review"),
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    search: Optional[str] = Query(None, description="Search in alert message"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page")
):
    """
    List alerts with optional filtering

    Query parameters:
    - status: Filter by alert status (suppressed, escalated, review)
    - severity: Filter by severity level
    - client_id: Filter by specific client
    - search: Search text in alert message
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 200)
    """
    try:
        pool = await get_pool()

        # Build query with filters
        where_clauses = []
        params = []
        param_count = 1

        if status:
            # Get status from audit.action_logs
            where_clauses.append(f"al.action = ${param_count}")
            params.append(status.upper())
            param_count += 1

        if severity:
            where_clauses.append(f"a.severity = ${param_count}")
            params.append(severity.upper())
            param_count += 1

        if client_id:
            where_clauses.append(f"a.client_id::text = ${param_count}")
            params.append(client_id)
            param_count += 1

        if search:
            where_clauses.append(f"a.message ILIKE ${param_count}")
            params.append(f"%{search}%")
            param_count += 1

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Count total
        count_query = f"""
            SELECT COUNT(*)
            FROM superops.alerts a
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.id::text
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            {where_sql}
        """
        total_count = await pool.fetchval(count_query, *params)

        # Get paginated results
        offset = (page - 1) * page_size
        params.extend([page_size, offset])

        query = f"""
            SELECT
                a.id,
                a.alert_id,
                a.client_id,
                c.client_name,
                a.asset_id,
                ast.asset_name,
                a.message,
                a.severity,
                a.source,
                a.created_at,
                ml.classification as ml_classification,
                ml.confidence as ml_confidence,
                al.action as ml_action,
                COALESCE(al.action, 'pending') as status
            FROM superops.alerts a
            LEFT JOIN superops.clients c ON c.id = a.client_id
            LEFT JOIN superops.assets ast ON ast.id = a.asset_id
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.id::text
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            {where_sql}
            ORDER BY a.created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        rows = await pool.fetch(query, *params)

        alerts = [
            AlertResponse(
                id=str(row['id']),
                alert_id=row['alert_id'],
                client_id=str(row['client_id']) if row['client_id'] else None,
                client_name=row['client_name'],
                asset_id=str(row['asset_id']) if row['asset_id'] else None,
                asset_name=row['asset_name'],
                message=row['message'],
                severity=row['severity'],
                source=row['source'],
                created_at=row['created_at'],
                status=row['status'],
                ml_classification=row['ml_classification'],
                ml_confidence=float(row['ml_confidence']) if row['ml_confidence'] else None,
                ml_action=row['ml_action']
            )
            for row in rows
        ]

        return AlertListResponse(
            alerts=alerts,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get detailed information about a specific alert"""
    try:
        pool = await get_pool()

        query = """
            SELECT
                a.id,
                a.alert_id,
                a.client_id,
                c.client_name,
                a.asset_id,
                ast.asset_name,
                a.message,
                a.severity,
                a.source,
                a.created_at,
                ml.classification as ml_classification,
                ml.confidence as ml_confidence,
                al.action as ml_action,
                COALESCE(al.action, 'pending') as status
            FROM superops.alerts a
            LEFT JOIN superops.clients c ON c.id = a.client_id
            LEFT JOIN superops.assets ast ON ast.id = a.asset_id
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.id::text
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            WHERE a.id = $1::uuid
        """

        row = await pool.fetchrow(query, alert_id)

        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")

        return AlertResponse(
            id=str(row['id']),
            alert_id=row['alert_id'],
            client_id=str(row['client_id']) if row['client_id'] else None,
            client_name=row['client_name'],
            asset_id=str(row['asset_id']) if row['asset_id'] else None,
            asset_name=row['asset_name'],
            message=row['message'],
            severity=row['severity'],
            source=row['source'],
            created_at=row['created_at'],
            status=row['status'],
            ml_classification=row['ml_classification'],
            ml_confidence=float(row['ml_confidence']) if row['ml_confidence'] else None,
            ml_action=row['ml_action']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch alert: {str(e)}")
