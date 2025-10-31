"""
Audit log API routes
GET /api/audit-log - Get ML decision history and action logs
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-log", tags=["audit"])

# Response models
class AuditLogEntry(BaseModel):
    id: str
    alert_id: str
    alert_message: str
    client_name: Optional[str]
    action: str
    reasoning: Optional[str]
    confidence: Optional[float]
    performed_by: str
    timestamp: datetime

class AuditLogResponse(BaseModel):
    entries: List[AuditLogEntry]
    total_count: int
    page: int
    page_size: int


@router.get("", response_model=AuditLogResponse)
async def get_audit_log(
    action: Optional[str] = Query(None, description="Filter by action: AUTO_SUPPRESS, ESCALATE, REVIEW"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page")
):
    """
    Get audit log of ML decisions and actions

    Returns history of:
    - Auto-suppression decisions
    - Escalation decisions
    - Review queue additions
    - Confidence scores and reasoning

    Query parameters:
    - action: Filter by specific action type
    - client_id: Filter by client
    - page: Page number (default: 1)
    - page_size: Items per page (default: 50, max: 200)
    """
    try:
        pool = await get_pool()

        # Build query with filters
        where_clauses = []
        params = []
        param_count = 1

        if action:
            where_clauses.append(f"al.action = ${param_count}")
            params.append(action.upper())
            param_count += 1

        if client_id:
            where_clauses.append(f"a.client_id::text = ${param_count}")
            params.append(client_id)
            param_count += 1

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Count total
        count_query = f"""
            SELECT COUNT(*)
            FROM audit.action_logs al
            JOIN superops.alerts a ON a.id = al.alert_id
            {where_sql}
        """
        total_count = await pool.fetchval(count_query, *params)

        # Get paginated results
        offset = (page - 1) * page_size
        params.extend([page_size, offset])

        query = f"""
            SELECT
                al.id,
                al.alert_id,
                a.message as alert_message,
                c.client_name as client_name,
                al.action,
                al.reason as reasoning,
                al.confidence,
                al.performed_by,
                al.timestamp
            FROM audit.action_logs al
            JOIN superops.alerts a ON a.id = al.alert_id
            LEFT JOIN superops.clients c ON c.id = a.client_id
            {where_sql}
            ORDER BY al.timestamp DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        rows = await pool.fetch(query, *params)

        entries = [
            AuditLogEntry(
                id=str(row['id']),
                alert_id=str(row['alert_id']),
                alert_message=row['alert_message'],
                client_name=row['client_name'],
                action=row['action'],
                reasoning=row['reasoning'],
                confidence=float(row['confidence']) if row['confidence'] else None,
                performed_by=row['performed_by'],
                timestamp=row['timestamp']
            )
            for row in rows
        ]

        return AuditLogResponse(
            entries=entries,
            total_count=total_count,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error fetching audit log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit log: {str(e)}")
