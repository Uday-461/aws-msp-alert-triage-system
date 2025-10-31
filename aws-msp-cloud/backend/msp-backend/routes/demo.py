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
    Start continuous demo mode

    This will:
    1. Start the alert generator at specified rate
    2. Track demo session for status queries
    3. Allow frontend to show "live" mode
    """
    if demo_state.is_running:
        raise HTTPException(status_code=400, detail="Demo already running. Stop first before starting new session.")

    try:
        # Call alert generator /storm endpoint
        async with httpx.AsyncClient() as client:
            # Storm endpoint generates at high rate for duration
            # We'll use continuous mode instead if available
            response = await client.post(
                "http://172.20.0.24:8003/start",  # alert-generator IP
                json={
                    "rate_per_minute": request.rate_per_minute
                },
                timeout=5.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Alert generator failed to start: {response.text}"
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
                "http://172.20.0.24:8003/stop",
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
                await client.post("http://172.20.0.24:8003/stop", timeout=5.0)

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
