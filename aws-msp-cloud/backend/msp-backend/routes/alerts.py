"""
Alert management API routes
GET /api/alerts - List alerts with filtering
GET /api/alerts/{alert_id} - Get alert details

NOTE: Queries action_logs.metadata for alert data (Kafka-streaming architecture).
The system uses Kafka where alerts are not persisted to alerts table.
Alert data is preserved in action_logs.metadata JSONB column.
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

    NOTE: Queries action_logs.metadata for alert data (Kafka-streaming architecture)

    Query parameters:
    - status: Filter by action (AUTO_SUPPRESS, ESCALATE, MANUAL_REVIEW)
    - severity: Filter by severity level (from metadata)
    - client_id: Filter by specific client
    - search: Search text in duplicate_of message
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
            # Map status to action
            status_upper = status.upper()
            if status_upper in ['SUPPRESSED', 'SUPPRESS']:
                where_clauses.append(f"al.action = 'AUTO_SUPPRESS'")
            elif status_upper in ['ESCALATED', 'ESCALATE']:
                where_clauses.append(f"al.action = 'ESCALATE'")
            elif status_upper in ['REVIEW', 'MANUAL_REVIEW']:
                where_clauses.append(f"al.action = 'MANUAL_REVIEW'")
            elif status_upper in ['AUTO_SUPPRESS', 'ESCALATE', 'MANUAL_REVIEW']:
                where_clauses.append(f"al.action = ${param_count}")
                params.append(status_upper)
                param_count += 1

        if severity:
            where_clauses.append(f"(al.metadata->>'severity')::text = ${param_count}")
            params.append(severity.upper())
            param_count += 1

        if client_id:
            where_clauses.append(f"(al.metadata->>'client_id')::text = ${param_count}")
            params.append(client_id)
            param_count += 1

        if search:
            where_clauses.append(f"(al.metadata->>'duplicate_of')::text ILIKE ${param_count}")
            params.append(f"%{search}%")
            param_count += 1

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Count total
        count_query = f"""
            SELECT COUNT(*)
            FROM audit.action_logs al
            WHERE al.metadata->>'external_alert_id' IS NOT NULL
            {"AND " + " AND ".join(where_clauses) if where_clauses else ""}
        """
        total_count = await pool.fetchval(count_query, *params)

        # Get paginated results
        offset = (page - 1) * page_size
        params.extend([page_size, offset])

        query = f"""
            SELECT
                al.id,
                al.metadata->>'external_alert_id' as alert_id,
                al.metadata->>'client_id' as client_id,
                c.client_name,
                al.metadata->>'asset_id' as asset_id,
                ast.asset_name,
                al.metadata->>'duplicate_of' as message,
                COALESCE(al.metadata->>'severity', 'MEDIUM') as severity,
                al.metadata->>'source' as source,
                al.timestamp as created_at,
                al.classification as ml_classification,
                al.confidence as ml_confidence,
                al.action as ml_action,
                al.action as status
            FROM audit.action_logs al
            LEFT JOIN superops.clients c ON c.id::text = al.metadata->>'client_id'
            LEFT JOIN superops.assets ast ON ast.id::text = al.metadata->>'asset_id'
            WHERE al.metadata->>'external_alert_id' IS NOT NULL
            {"AND " + " AND ".join(where_clauses) if where_clauses else ""}
            ORDER BY al.timestamp DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        rows = await pool.fetch(query, *params)

        alerts = [
            AlertResponse(
                id=str(row['id']),
                alert_id=row['alert_id'] or 'UNKNOWN',
                client_id=row['client_id'],
                client_name=row['client_name'],
                asset_id=row['asset_id'],
                asset_name=row['asset_name'],
                message=row['message'] or 'No message',
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get detailed information about a specific alert"""
    try:
        pool = await get_pool()

        query = """
            SELECT
                al.id,
                al.metadata->>'external_alert_id' as alert_id,
                al.metadata->>'client_id' as client_id,
                c.client_name,
                al.metadata->>'asset_id' as asset_id,
                ast.asset_name,
                al.metadata->>'duplicate_of' as message,
                COALESCE(al.metadata->>'severity', 'MEDIUM') as severity,
                al.metadata->>'source' as source,
                al.timestamp as created_at,
                al.classification as ml_classification,
                al.confidence as ml_confidence,
                al.action as ml_action,
                al.action as status
            FROM audit.action_logs al
            LEFT JOIN superops.clients c ON c.id::text = al.metadata->>'client_id'
            LEFT JOIN superops.assets ast ON ast.id::text = al.metadata->>'asset_id'
            WHERE al.metadata->>'external_alert_id' = $1
            ORDER BY al.timestamp DESC
            LIMIT 1
        """

        row = await pool.fetchrow(query, alert_id)

        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")

        return AlertResponse(
            id=str(row['id']),
            alert_id=row['alert_id'] or 'UNKNOWN',
            client_id=row['client_id'],
            client_name=row['client_name'],
            asset_id=row['asset_id'],
            asset_name=row['asset_name'],
            message=row['message'] or 'No message',
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch alert: {str(e)}")
