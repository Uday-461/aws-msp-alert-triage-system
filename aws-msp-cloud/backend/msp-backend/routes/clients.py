"""
Client management API routes
GET /api/clients - List clients with alert counts
GET /api/clients/{client_id} - Get client details with alert statistics
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clients", tags=["clients"])

# Response models
class ClientSummary(BaseModel):
    id: str
    name: str
    tier: str
    total_alerts_24h: int
    suppressed_alerts_24h: int
    escalated_alerts_24h: int
    critical_alerts_24h: int
    active_assets: int

class ClientListResponse(BaseModel):
    clients: List[ClientSummary]
    total_count: int

class ClientDetailResponse(BaseModel):
    id: str
    name: str
    tier: str
    contact_email: Optional[str]
    total_assets: int
    active_assets: int

    # Alert statistics (last 24 hours)
    total_alerts_24h: int
    suppressed_alerts_24h: int
    escalated_alerts_24h: int
    review_alerts_24h: int
    critical_alerts_24h: int

    # Alert statistics (last 7 days)
    total_alerts_7d: int
    suppression_rate_7d: float

    # Asset breakdown
    server_count: int
    workstation_count: int
    network_count: int


@router.get("", response_model=ClientListResponse)
async def list_clients():
    """
    List all clients with 24-hour alert statistics
    """
    try:
        pool = await get_pool()

        # Time range: last 24 hours
        start_time = datetime.utcnow() - timedelta(hours=24)

        query = """
            SELECT
                c.id,
                c.client_name,
                c.tier,
                COUNT(DISTINCT ast.id) as active_assets,
                COUNT(a.id) FILTER (WHERE a.created_at >= $1) as total_alerts_24h,
                COUNT(a.id) FILTER (WHERE a.created_at >= $1 AND al.action = 'AUTO_SUPPRESS') as suppressed_24h,
                COUNT(a.id) FILTER (WHERE a.created_at >= $1 AND al.action = 'ESCALATE') as escalated_24h,
                COUNT(a.id) FILTER (WHERE a.created_at >= $1 AND a.severity = 'CRITICAL') as critical_24h
            FROM superops.clients c
            LEFT JOIN superops.assets ast ON ast.client_id = c.id
            LEFT JOIN superops.alerts a ON a.client_id = c.id
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.alert_id
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            GROUP BY c.id, c.client_name, c.tier
            ORDER BY c.client_name
        """

        rows = await pool.fetch(query, start_time)

        clients = [
            ClientSummary(
                id=str(row['id']),
                name=row['client_name'],
                tier=row['tier'],
                total_alerts_24h=row['total_alerts_24h'],
                suppressed_alerts_24h=row['suppressed_24h'],
                escalated_alerts_24h=row['escalated_24h'],
                critical_alerts_24h=row['critical_24h'],
                active_assets=row['active_assets']
            )
            for row in rows
        ]

        return ClientListResponse(
            clients=clients,
            total_count=len(clients)
        )

    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clients: {str(e)}")


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(client_id: str):
    """
    Get detailed client information with alert statistics
    """
    try:
        pool = await get_pool()

        # Get client info
        client_query = """
            SELECT id, client_name, tier, contact_email
            FROM superops.clients
            WHERE id = $1
        """

        client_row = await pool.fetchrow(client_query, client_id)

        if not client_row:
            raise HTTPException(status_code=404, detail="Client not found")

        # Get asset statistics
        asset_query = """
            SELECT
                COUNT(*) as total_assets,
                COUNT(*) FILTER (WHERE status = 'active') as active_assets,
                COUNT(*) FILTER (WHERE asset_type = 'server') as server_count,
                COUNT(*) FILTER (WHERE asset_type = 'workstation') as workstation_count,
                COUNT(*) FILTER (WHERE asset_type = 'network_device') as network_count
            FROM superops.assets
            WHERE client_id = $1
        """

        asset_stats = await pool.fetchrow(asset_query, client_id)

        # Get 24-hour alert statistics
        start_24h = datetime.utcnow() - timedelta(hours=24)

        alert_24h_query = """
            SELECT
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE al.action = 'AUTO_SUPPRESS') as suppressed,
                COUNT(*) FILTER (WHERE al.action = 'ESCALATE') as escalated,
                COUNT(*) FILTER (WHERE al.action = 'REVIEW') as review,
                COUNT(*) FILTER (WHERE a.severity = 'CRITICAL') as critical
            FROM superops.alerts a
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.alert_id
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            WHERE a.client_id = $1
              AND a.created_at >= $2
        """

        alert_24h = await pool.fetchrow(alert_24h_query, client_id, start_24h)

        # Get 7-day alert statistics
        start_7d = datetime.utcnow() - timedelta(days=7)

        alert_7d_query = """
            SELECT
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE al.action = 'AUTO_SUPPRESS') as suppressed
            FROM superops.alerts a
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.alert_id
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            WHERE a.client_id = $1
              AND a.created_at >= $2
        """

        alert_7d = await pool.fetchrow(alert_7d_query, client_id, start_7d)

        # Calculate 7-day suppression rate
        total_7d = alert_7d['total_alerts'] or 0
        suppressed_7d = alert_7d['suppressed'] or 0
        suppression_rate_7d = (suppressed_7d / total_7d * 100) if total_7d > 0 else 0

        return ClientDetailResponse(
            id=str(client_row['id']),
            name=client_row['client_name'],
            tier=client_row['tier'],
            contact_email=client_row['contact_email'],
            total_assets=asset_stats['total_assets'],
            active_assets=asset_stats['active_assets'],
            total_alerts_24h=alert_24h['total_alerts'],
            suppressed_alerts_24h=alert_24h['suppressed'],
            escalated_alerts_24h=alert_24h['escalated'],
            review_alerts_24h=alert_24h['review'],
            critical_alerts_24h=alert_24h['critical'],
            total_alerts_7d=total_7d,
            suppression_rate_7d=round(suppression_rate_7d, 2),
            server_count=asset_stats['server_count'],
            workstation_count=asset_stats['workstation_count'],
            network_count=asset_stats['network_count']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch client details: {str(e)}")
