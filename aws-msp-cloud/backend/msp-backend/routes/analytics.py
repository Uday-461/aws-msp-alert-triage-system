"""
Analytics API routes
GET /api/analytics/volume - Get alert volume over time
GET /api/analytics/classification-distribution - Get classification breakdown
GET /api/analytics/latency-distribution - Get latency histogram data
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging

from database import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Response models
class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    total: int
    suppressed: int
    escalated: int
    suppression_rate: float

class VolumeResponse(BaseModel):
    data: List[TimeSeriesPoint]
    time_range: str
    total_points: int

class ClassificationBreakdown(BaseModel):
    classification: str
    count: int
    percentage: float
    color: str

class ClassificationDistributionResponse(BaseModel):
    data: List[ClassificationBreakdown]
    total: int
    time_range: str

class LatencyBucket(BaseModel):
    range: str
    min_ms: float
    max_ms: float
    count: int
    percentage: float

class LatencyDistributionResponse(BaseModel):
    data: List[LatencyBucket]
    total: int
    avg_latency_ms: float
    time_range: str


@router.get("/volume", response_model=VolumeResponse)
async def get_alert_volume(
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$", description="Time range: 1h, 24h, 7d, or 30d")
):
    """
    Get alert volume over time with suppression rates

    Returns time-series data grouped by hour (for 1h, 24h) or day (for 7d, 30d)
    """
    try:
        pool = await get_pool()

        # Parse time range
        range_map = {
            "1h": (1, "hour"),
            "24h": (24, "hour"),
            "7d": (7 * 24, "day"),
            "30d": (30 * 24, "day")
        }

        hours, group_by = range_map[time_range]
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Determine grouping interval
        if group_by == "hour":
            interval = "1 hour"
            trunc_format = "hour"
        else:
            interval = "1 day"
            trunc_format = "day"

        # Query alert volume grouped by time
        query = f"""
            SELECT
                date_trunc('{trunc_format}', created_at) as timestamp,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE classification IN ('NOISE', 'DUPLICATE')) as suppressed,
                COUNT(*) FILTER (WHERE classification IN ('ACTIONABLE', 'CRITICAL')) as escalated
            FROM superops.ml_classifications
            WHERE created_at >= $1
            GROUP BY date_trunc('{trunc_format}', created_at)
            ORDER BY timestamp ASC
        """

        rows = await pool.fetch(query, start_time)

        # Build time series data
        data = []
        for row in rows:
            total = row['total']
            suppressed = row['suppressed']
            escalated = row['escalated']
            suppression_rate = (suppressed / total * 100) if total > 0 else 0

            data.append(TimeSeriesPoint(
                timestamp=row['timestamp'],
                total=total,
                suppressed=suppressed,
                escalated=escalated,
                suppression_rate=round(suppression_rate, 2)
            ))

        return VolumeResponse(
            data=data,
            time_range=time_range,
            total_points=len(data)
        )

    except Exception as e:
        logger.error(f"Error getting alert volume: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert volume: {str(e)}")


@router.get("/classification-distribution", response_model=ClassificationDistributionResponse)
async def get_classification_distribution(
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$", description="Time range: 1h, 24h, 7d, or 30d")
):
    """
    Get classification distribution (pie chart data)

    Returns breakdown by classification type with counts and percentages
    """
    try:
        pool = await get_pool()

        # Parse time range
        range_map = {"1h": 1, "24h": 24, "7d": 7 * 24, "30d": 30 * 24}
        hours = range_map[time_range]
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Query classification distribution
        query = """
            SELECT
                classification,
                COUNT(*) as count
            FROM superops.ml_classifications
            WHERE created_at >= $1
            GROUP BY classification
            ORDER BY count DESC
        """

        rows = await pool.fetch(query, start_time)

        # Calculate total and percentages
        total = sum(row['count'] for row in rows)

        # Color mapping for classifications
        color_map = {
            'DUPLICATE': '#3b82f6',  # blue
            'NOISE': '#6b7280',      # gray
            'ACTIONABLE': '#f59e0b', # amber
            'CRITICAL': '#ef4444',   # red
        }

        # Build distribution data
        data = []
        for row in rows:
            classification = row['classification'] or 'UNKNOWN'
            count = row['count']
            percentage = (count / total * 100) if total > 0 else 0

            data.append(ClassificationBreakdown(
                classification=classification,
                count=count,
                percentage=round(percentage, 2),
                color=color_map.get(classification, '#9ca3af')
            ))

        return ClassificationDistributionResponse(
            data=data,
            total=total,
            time_range=time_range
        )

    except Exception as e:
        logger.error(f"Error getting classification distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get classification distribution: {str(e)}")


@router.get("/latency-distribution", response_model=LatencyDistributionResponse)
async def get_latency_distribution(
    time_range: str = Query("24h", regex="^(1h|24h|7d|30d)$", description="Time range: 1h, 24h, 7d, or 30d")
):
    """
    Get ML latency distribution (histogram data)

    Returns latency buckets with counts and percentages
    """
    try:
        pool = await get_pool()

        # Parse time range
        range_map = {"1h": 1, "24h": 24, "7d": 7 * 24, "30d": 30 * 24}
        hours = range_map[time_range]
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Query latency statistics
        query = """
            SELECT
                total_latency_ms,
                COUNT(*) OVER() as total_count,
                AVG(total_latency_ms) OVER() as avg_latency
            FROM superops.ml_classifications
            WHERE created_at >= $1
              AND total_latency_ms IS NOT NULL
        """

        rows = await pool.fetch(query, start_time)

        if not rows:
            return LatencyDistributionResponse(
                data=[],
                total=0,
                avg_latency_ms=0.0,
                time_range=time_range
            )

        total_count = rows[0]['total_count']
        avg_latency = float(rows[0]['avg_latency'])

        # Define latency buckets
        buckets = [
            {"range": "<10ms", "min": 0, "max": 10},
            {"range": "10-50ms", "min": 10, "max": 50},
            {"range": "50-100ms", "min": 50, "max": 100},
            {"range": "100-200ms", "min": 100, "max": 200},
            {"range": "200-500ms", "min": 200, "max": 500},
            {"range": "500ms+", "min": 500, "max": float('inf')},
        ]

        # Count classifications in each bucket
        bucket_counts = {b["range"]: 0 for b in buckets}

        for row in rows:
            latency = row['total_latency_ms']
            for bucket in buckets:
                if bucket["min"] <= latency < bucket["max"]:
                    bucket_counts[bucket["range"]] += 1
                    break

        # Build histogram data
        data = []
        for bucket in buckets:
            count = bucket_counts[bucket["range"]]
            percentage = (count / total_count * 100) if total_count > 0 else 0

            data.append(LatencyBucket(
                range=bucket["range"],
                min_ms=bucket["min"],
                max_ms=bucket["max"] if bucket["max"] != float('inf') else 999999,
                count=count,
                percentage=round(percentage, 2)
            ))

        return LatencyDistributionResponse(
            data=data,
            total=total_count,
            avg_latency_ms=round(avg_latency, 2),
            time_range=time_range
        )

    except Exception as e:
        logger.error(f"Error getting latency distribution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get latency distribution: {str(e)}")
