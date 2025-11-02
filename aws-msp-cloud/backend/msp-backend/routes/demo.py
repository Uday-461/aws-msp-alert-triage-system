"""
Demo control endpoints for frontend showcase
Provides start/pause/reset/status endpoints for continuous demo mode
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])

# Demo state (in-memory for now)
class DemoState:
    def __init__(self):
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.alerts_sent = 0
        self.rate_per_minute = 60

demo_state = DemoState()

# Request models
class StartDemoRequest(BaseModel):
    rate_per_minute: int = Field(60, ge=10, le=1200, description="Alerts per minute (10-1200)")
    duration_minutes: Optional[int] = Field(None, ge=1, le=60, description="Optional duration limit")

class DemoStatusResponse(BaseModel):
    is_running: bool
    start_time: Optional[datetime]
    elapsed_seconds: Optional[float]
    alerts_sent: int
    rate_per_minute: int
    estimated_alerts_processed: int  # Based on time elapsed


@router.post("/start")
async def start_demo(request: StartDemoRequest):
    """
    Start continuous demo mode (Smart Start with auto-stop)

    This will:
    1. Check if alert generator is already running
    2. Auto-stop if needed (prevents 400 Bad Request errors)
    3. Start the alert generator at specified rate
    4. Track demo session for status queries
    5. Allow frontend to show "live" mode
    """
    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Check alert generator status first
            status_response = await client.get(
                "http://172.20.0.24:8003/status",
                timeout=5.0
            )

            if status_response.status_code == 200:
                status_data = status_response.json()

                # Step 2: If already generating, stop first
                if status_data.get("is_generating", False):
                    logger.info(
                        f"Alert generation already active at {status_data.get('current_rate', 'unknown')} alerts/min. "
                        f"Auto-stopping before restart..."
                    )

                    stop_response = await client.post(
                        "http://172.20.0.24:8003/stop",
                        timeout=5.0
                    )

                    if stop_response.status_code != 200:
                        logger.warning(f"Alert generator stop returned {stop_response.status_code}: {stop_response.text}")

                    # Brief delay to ensure clean stop
                    import asyncio
                    await asyncio.sleep(0.5)

                    logger.info("Alert generation stopped successfully. Starting fresh session...")

            # Step 3: Start alert generation
            response = await client.post(
                "http://172.20.0.24:8003/start",
                json={
                    "rate_per_minute": request.rate_per_minute
                },
                timeout=5.0
            )

            # Step 4: Handle errors with proper status codes
            if response.status_code == 400:
                # Should not happen after stop, but handle gracefully
                raise HTTPException(
                    status_code=409,  # Conflict (not 500)
                    detail=f"Alert generator in unexpected state: {response.text}. "
                           "Try pause/reset first, or contact support if issue persists."
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,  # Bad Gateway (more accurate than 500)
                    detail=f"Alert generator error ({response.status_code}): {response.text}"
                )

        # Update demo state
        demo_state.is_running = True
        demo_state.start_time = datetime.now(timezone.utc)
        demo_state.alerts_sent = 0
        demo_state.rate_per_minute = request.rate_per_minute

        return {
            "status": "demo_started",
            "rate_per_minute": request.rate_per_minute,
            "start_time": demo_state.start_time,
            "message": "Demo mode active - alerts flowing through ML pipeline"
        }

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to alert generator: {str(e)}"
        )


@router.post("/pause")
async def pause_demo():
    """
    Pause the demo (stop alert generation but keep session)
    """
    if not demo_state.is_running:
        raise HTTPException(status_code=400, detail="Demo not running")

    try:
        # Call alert generator /stop endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://172.20.0.24:8003/stop",  # alert-generator IP
                timeout=5.0
            )

            if response.status_code != 200:
                logger.warning(f"Alert generator stop failed: {response.text}")

        demo_state.is_running = False

        return {
            "status": "demo_paused",
            "alerts_sent": demo_state.alerts_sent,
            "elapsed_seconds": (datetime.now(timezone.utc) - demo_state.start_time).total_seconds() if demo_state.start_time else 0
        }

    except httpx.RequestError as e:
        logger.error(f"Error stopping alert generator: {e}")
        # Still mark as paused even if generator call fails
        demo_state.is_running = False
        return {
            "status": "demo_paused",
            "warning": "Alert generator may still be running"
        }


@router.post("/reset")
async def reset_demo():
    """
    Reset demo (stop generation, clear recent classifications)

    WARNING: This will DELETE recent ML classifications from the database
    Use only for demo/testing purposes
    """
    try:
        # Stop alert generation first
        if demo_state.is_running:
            async with httpx.AsyncClient() as client:
                await client.post("http://172.20.0.24:8003/stop", timeout=5.0)  # alert-generator IP

        # Reset demo state
        reset_time = demo_state.start_time or (datetime.now(timezone.utc) - timedelta(hours=1))
        demo_state.is_running = False
        demo_state.start_time = None
        demo_state.alerts_sent = 0

        # Clear recent classifications (only since demo started)
        from database import get_pool
        pool = await get_pool()

        deleted = await pool.fetchval(
            """
            DELETE FROM superops.ml_classifications
            WHERE created_at >= $1
            RETURNING COUNT(*)
            """,
            reset_time
        )

        return {
            "status": "demo_reset",
            "classifications_deleted": deleted or 0,
            "message": "Demo reset - ready for new session"
        }

    except Exception as e:
        logger.error(f"Error resetting demo: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@router.post("/reset-full")
async def reset_demo_full(confirm: bool = False):
    """
    Full reset: Delete ALL alerts, classifications, and action logs since 2025-11-01

    This is a comprehensive reset that:
    1. Stops alert generation if running
    2. Deletes action_logs (no FK constraints)
    3. Deletes ml_classifications (references alerts)
    4. Deletes alerts (keeps seed data before 2025-11-01)
    5. Resets demo state

    WARNING: This will DELETE all alerts generated since Nov 1, 2025
    Use only for demo/testing purposes

    Args:
        confirm: Must be True to proceed (safety check)
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=True to proceed with full reset"
        )

    try:
        # Step 1: Stop alert generation first
        if demo_state.is_running:
            async with httpx.AsyncClient() as client:
                await client.post("http://172.20.0.24:8003/stop", timeout=5.0)

        # Step 2: Get cutoff date (Nov 1, 2025 - keeps seed data)
        cutoff_date = datetime(2025, 11, 1, tzinfo=timezone.utc)

        from database import get_pool
        pool = await get_pool()

        # Step 3: Delete in correct order (avoid FK violations)

        # 3a. Delete action_logs (no FK constraints, safe to delete first)
        action_logs_deleted = await pool.fetchval(
            """
            WITH deleted AS (
                DELETE FROM audit.action_logs
                WHERE timestamp >= $1
                RETURNING 1
            )
            SELECT COUNT(*) FROM deleted
            """,
            cutoff_date
        ) or 0

        # 3b. Delete ml_classifications (references alerts via FK)
        classifications_deleted = await pool.fetchval(
            """
            WITH deleted AS (
                DELETE FROM superops.ml_classifications
                WHERE created_at >= $1
                RETURNING 1
            )
            SELECT COUNT(*) FROM deleted
            """,
            cutoff_date
        ) or 0

        # 3c. Delete alerts (keep seed data before Nov 1)
        alerts_deleted = await pool.fetchval(
            """
            WITH deleted AS (
                DELETE FROM superops.alerts
                WHERE created_at >= $1
                RETURNING 1
            )
            SELECT COUNT(*) FROM deleted
            """,
            cutoff_date
        ) or 0

        # Step 4: Reset demo state
        demo_state.is_running = False
        demo_state.start_time = None
        demo_state.alerts_sent = 0

        logger.info(
            f"Full reset complete: {alerts_deleted} alerts, "
            f"{classifications_deleted} classifications, {action_logs_deleted} action logs deleted"
        )

        return {
            "status": "full_reset_complete",
            "deleted": {
                "alerts": alerts_deleted,
                "ml_classifications": classifications_deleted,
                "action_logs": action_logs_deleted
            },
            "cutoff_date": cutoff_date.isoformat(),
            "message": "All demo data deleted. Seed data preserved. Ready for fresh demo."
        }

    except Exception as e:
        logger.error(f"Error in full reset: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Full reset failed: {str(e)}")


@router.get("/status", response_model=DemoStatusResponse)
async def get_demo_status():
    """
    Get current demo status and statistics

    Returns:
        - is_running: Whether demo is active
        - start_time: When demo started (if running)
        - elapsed_seconds: How long demo has been running
        - alerts_sent: Alerts generated (estimated based on rate)
        - rate_per_minute: Current generation rate
        - estimated_alerts_processed: Estimated alerts processed by ML pipeline
    """
    elapsed_seconds = 0
    estimated_alerts = 0

    if demo_state.start_time:
        elapsed_seconds = (datetime.now(timezone.utc) - demo_state.start_time).total_seconds()
        # Estimate alerts sent based on rate and time
        estimated_alerts = int((demo_state.rate_per_minute / 60) * elapsed_seconds)

    # Get actual processed count from database
    from database import get_pool
    pool = await get_pool()

    processed_count = 0
    if demo_state.start_time:
        processed_count = await pool.fetchval(
            "SELECT COUNT(*) FROM superops.ml_classifications WHERE created_at >= $1",
            demo_state.start_time
        ) or 0

    return DemoStatusResponse(
        is_running=demo_state.is_running,
        start_time=demo_state.start_time,
        elapsed_seconds=elapsed_seconds if demo_state.start_time else None,
        alerts_sent=estimated_alerts,
        rate_per_minute=demo_state.rate_per_minute,
        estimated_alerts_processed=processed_count
    )
