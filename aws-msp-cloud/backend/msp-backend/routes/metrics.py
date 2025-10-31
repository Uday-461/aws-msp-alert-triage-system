"""
Metrics and statistics API routes
GET /api/metrics - Get dashboard metrics (suppression rate, escalation rate, ROI)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import logging

from database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# Response models
class MetricsResponse(BaseModel):
    # Alert statistics
    total_alerts: int
    suppressed_alerts: int
    escalated_alerts: int
    review_alerts: int
    suppression_rate: float
    escalation_rate: float

    # ML performance
    avg_ml_latency_ms: Optional[float]
    avg_ml_confidence: Optional[float]

    # Time savings
    alerts_processed_24h: int
    time_saved_hours: float
    cost_saved_usd: float

    # ROI metrics
    roi_annual_usd: float
    roi_weekly_hours: float

    # Category breakdown (Phase 2)
    category_distribution: dict

    # Timestamp
    calculated_at: datetime
    time_range_hours: int


@router.get("", response_model=MetricsResponse)
async def get_metrics(
    hours: int = Query(24, ge=1, le=720, description="Time range in hours (default: 24, max: 168)")
):
    """
    Get dashboard metrics and statistics

    Calculates:
    - Alert suppression and escalation rates
    - ML pipeline performance
    - Time and cost savings
    - Annual ROI projections
    - Category distribution (Phase 2)
    """
    try:
        pool = await get_pool()

        # Time range
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Get alert statistics
        alert_stats_query = """
            SELECT
                COUNT(*) as total_alerts,
                COUNT(*) FILTER (WHERE al.action = 'AUTO_SUPPRESS') as suppressed,
                COUNT(*) FILTER (WHERE al.action = 'ESCALATE') as escalated,
                COUNT(*) FILTER (WHERE al.action = 'REVIEW') as review,
                AVG(ml.total_latency_ms) as avg_latency,
                AVG(ml.confidence) as avg_confidence
            FROM superops.alerts a
            LEFT JOIN superops.ml_classifications ml ON ml.alert_id = a.id::text
            LEFT JOIN audit.action_logs al ON al.alert_id = a.id
            WHERE a.created_at >= $1
        """

        stats = await pool.fetchrow(alert_stats_query, start_time)

        total_alerts = stats['total_alerts'] or 0
        suppressed = stats['suppressed'] or 0
        escalated = stats['escalated'] or 0
        review = stats['review'] or 0

        # Calculate rates
        suppression_rate = (suppressed / total_alerts * 100) if total_alerts > 0 else 0
        escalation_rate = (escalated / total_alerts * 100) if total_alerts > 0 else 0

        # ML performance
        avg_ml_latency_ms = float(stats['avg_latency']) if stats['avg_latency'] else None
        avg_ml_confidence = float(stats['avg_confidence']) if stats['avg_confidence'] else None

        # Category distribution (Phase 2)
        # Note: alert_category column doesn't exist yet in schema
        # Return empty distribution for now
        category_distribution = {}

        # Time and cost savings calculation
        # Assumption: Each suppressed alert saves 5 minutes of engineer time
        # Engineer hourly rate: $75/hour
        minutes_per_alert = 5
        hourly_rate = 75

        time_saved_hours = (suppressed * minutes_per_alert) / 60
        cost_saved_usd = time_saved_hours * hourly_rate

        # Annual ROI projection
        # Extrapolate from current time range to annual
        hours_in_year = 24 * 365
        extrapolation_factor = hours_in_year / hours

        roi_annual_usd = cost_saved_usd * extrapolation_factor
        roi_weekly_hours = time_saved_hours * (168 / hours)  # 168 hours in a week

        return MetricsResponse(
            total_alerts=total_alerts,
            suppressed_alerts=suppressed,
            escalated_alerts=escalated,
            review_alerts=review,
            suppression_rate=round(suppression_rate, 2),
            escalation_rate=round(escalation_rate, 2),
            avg_ml_latency_ms=round(avg_ml_latency_ms, 2) if avg_ml_latency_ms else None,
            avg_ml_confidence=round(avg_ml_confidence, 4) if avg_ml_confidence else None,
            alerts_processed_24h=total_alerts,
            time_saved_hours=round(time_saved_hours, 2),
            cost_saved_usd=round(cost_saved_usd, 2),
            roi_annual_usd=round(roi_annual_usd, 2),
            roi_weekly_hours=round(roi_weekly_hours, 2),
            category_distribution=category_distribution,
            calculated_at=datetime.utcnow(),
            time_range_hours=hours
        )

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate metrics: {str(e)}")
