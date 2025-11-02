"""
Alert Lifecycle API Routes
Provides REST endpoints for managing alert lifecycle states
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from services.alert_lifecycle import AlertLifecycle, AlertStatus
from database import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lifecycle", tags=["Alert Lifecycle"])


# ===== Pydantic Models =====

class TransitionRequest(BaseModel):
    """Request model for state transitions"""
    alert_id: str = Field(..., description="UUID of the alert")
    new_status: AlertStatus = Field(..., description="Target status")
    assigned_to: Optional[str] = Field(None, description="Assign to user")
    notes: Optional[str] = Field(None, description="Transition notes")
    changed_by: str = Field("system", description="User performing transition")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class AssignmentRequest(BaseModel):
    """Request model for alert assignments"""
    alert_id: str = Field(..., description="UUID of the alert")
    assignee: str = Field(..., description="User to assign to")
    changed_by: str = Field("system", description="User performing assignment")
    notes: Optional[str] = Field(None, description="Assignment notes")


class BulkUpdateRequest(BaseModel):
    """Request model for bulk status updates"""
    alert_ids: List[str] = Field(..., description="List of alert UUIDs")
    new_status: AlertStatus = Field(..., description="Target status")
    changed_by: str = Field("system", description="User performing update")
    notes: Optional[str] = Field(None, description="Update notes")


class TransitionResponse(BaseModel):
    """Response model for transitions"""
    alert_id: str
    old_status: Optional[str]
    new_status: str
    changed_by: str
    duration_ms: Optional[int]
    assigned_to: Optional[str]
    timestamp: str


class AssignmentResponse(BaseModel):
    """Response model for assignments"""
    alert_id: str
    assigned_to: str
    changed_by: str
    status: str
    timestamp: str


class HistoryResponse(BaseModel):
    """Response model for lifecycle history"""
    alert_id: str
    history: List[dict]
    total_transitions: int


class StatusResponse(BaseModel):
    """Response model for current status"""
    alert_id: str
    status: str
    assigned_to: Optional[str]
    transitioned_by: Optional[str]
    transitioned_at: datetime
    metadata: Optional[dict]


class MetricsResponse(BaseModel):
    """Response model for lifecycle metrics"""
    total_transitions: int
    state_distribution: List[dict]
    average_durations: List[dict]
    period: dict


# ===== Dependency Injection =====

async def get_lifecycle_service() -> AlertLifecycle:
    """Dependency to get AlertLifecycle service instance"""
    db_pool = await get_db_pool()
    return AlertLifecycle(db_pool)


# ===== API Endpoints =====

@router.post("/transition", response_model=TransitionResponse)
async def transition_alert(
    request: TransitionRequest,
    lifecycle: AlertLifecycle = Depends(get_lifecycle_service)
):
    """
    Transition alert to new status.

    Validates state machine transitions and records complete audit trail.

    **Valid Transitions:**
    - new → investigating
    - investigating → resolved, reopened
    - resolved → closed, reopened
    - closed → reopened
    - reopened → investigating

    **Returns:**
    - Transition details including old/new status and duration

    **Raises:**
    - 400: Invalid transition
    - 404: Alert not found
    - 500: Database error
    """
    try:
        result = await lifecycle.transition(
            alert_id=request.alert_id,
            new_status=request.new_status,
            assigned_to=request.assigned_to,
            notes=request.notes,
            changed_by=request.changed_by,
            metadata=request.metadata
        )
        return TransitionResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid transition request: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error transitioning alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to transition alert")


@router.get("/history/{alert_id}", response_model=HistoryResponse)
async def get_alert_history(
    alert_id: str,
    lifecycle: AlertLifecycle = Depends(get_lifecycle_service)
):
    """
    Get complete lifecycle history for an alert.

    Returns chronologically ordered list of all state transitions,
    assignments, and associated metadata.

    **Returns:**
    - Complete lifecycle history with timestamps and durations

    **Raises:**
    - 404: Alert not found or no history
    - 500: Database error
    """
    try:
        history = await lifecycle.get_history(alert_id)

        if not history:
            raise HTTPException(
                status_code=404,
                detail=f"No lifecycle history found for alert {alert_id}"
            )

        return HistoryResponse(
            alert_id=alert_id,
            history=history,
            total_transitions=len(history)
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error fetching alert history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert history")


@router.get("/status/{alert_id}", response_model=StatusResponse)
async def get_current_status(
    alert_id: str,
    lifecycle: AlertLifecycle = Depends(get_lifecycle_service)
):
    """
    Get current lifecycle status for an alert.

    Returns most recent state, assignment, and transition details.

    **Returns:**
    - Current status with assignment and metadata

    **Raises:**
    - 404: Alert not found or no lifecycle records
    - 500: Database error
    """
    try:
        status = await lifecycle.get_current_status(alert_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"No lifecycle status found for alert {alert_id}"
            )

        return StatusResponse(
            alert_id=alert_id,
            status=status['status'],
            assigned_to=status.get('assigned_to'),
            transitioned_by=status.get('transitioned_by'),
            transitioned_at=status['transitioned_at'],
            metadata=status.get('metadata')
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error fetching current status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch current status")


@router.post("/assign", response_model=AssignmentResponse)
async def assign_alert(
    request: AssignmentRequest,
    lifecycle: AlertLifecycle = Depends(get_lifecycle_service)
):
    """
    Assign alert to a user without changing status.

    Creates lifecycle record tracking assignment change while
    maintaining current state.

    **Returns:**
    - Assignment details with timestamp

    **Raises:**
    - 404: Alert not found
    - 500: Database error
    """
    try:
        result = await lifecycle.assign_to_user(
            alert_id=request.alert_id,
            assignee=request.assignee,
            changed_by=request.changed_by,
            notes=request.notes
        )
        return AssignmentResponse(**result)

    except Exception as e:
        logger.error(f"Error assigning alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign alert")


@router.get("/metrics", response_model=MetricsResponse)
async def get_lifecycle_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    lifecycle: AlertLifecycle = Depends(get_lifecycle_service)
):
    """
    Get lifecycle metrics and analytics.

    Returns aggregate statistics including:
    - State distribution (count per state)
    - Average transition durations
    - Total transition count

    **Query Parameters:**
    - start_date: Filter transitions after this date
    - end_date: Filter transitions before this date

    **Returns:**
    - Comprehensive metrics for specified period

    **Raises:**
    - 500: Database error
    """
    try:
        metrics = await lifecycle.get_metrics(
            start_date=start_date,
            end_date=end_date
        )
        return MetricsResponse(**metrics)

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


@router.post("/bulk-update")
async def bulk_update_status(
    request: BulkUpdateRequest,
    lifecycle: AlertLifecycle = Depends(get_lifecycle_service)
):
    """
    Bulk update status for multiple alerts.

    Transitions multiple alerts to the same status in a single operation.
    Each transition is validated independently.

    **Returns:**
    - Success/failure counts with details

    **Note:**
    - Partial success possible (some alerts succeed, others fail)
    - Failed alerts include error details

    **Raises:**
    - 400: Invalid request
    - 500: Database error
    """
    try:
        if not request.alert_ids:
            raise HTTPException(status_code=400, detail="No alert IDs provided")

        if len(request.alert_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot update more than 100 alerts at once"
            )

        results = await lifecycle.bulk_update_status(
            alert_ids=request.alert_ids,
            new_status=request.new_status,
            changed_by=request.changed_by,
            notes=request.notes
        )

        return {
            "total": results["total"],
            "successful": len(results["successful"]),
            "failed": len(results["failed"]),
            "details": results
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk update alerts")


@router.get("/valid-transitions/{current_status}")
async def get_valid_transitions(current_status: str):
    """
    Get valid next states for a given current status.

    Useful for UI to show only valid transition options.

    **Returns:**
    - List of valid next states

    **Raises:**
    - 400: Invalid status provided
    """
    try:
        status = AlertStatus(current_status)
        valid_next = AlertLifecycle.VALID_TRANSITIONS.get(status, [])

        return {
            "current_status": status.value,
            "valid_next_states": [s.value for s in valid_next]
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {current_status}. Valid values: {[s.value for s in AlertStatus]}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for lifecycle API"""
    return {
        "status": "healthy",
        "service": "alert-lifecycle",
        "timestamp": datetime.now().isoformat()
    }
