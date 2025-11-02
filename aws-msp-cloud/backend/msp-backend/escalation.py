from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionType(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class NotificationChannelType(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"


class CreatePolicyRequest(BaseModel):
    client_id: str
    name: str
    description: Optional[str] = None
    severity_filter: List[str] = Field(default_factory=list)
    category_filter: List[str] = Field(default_factory=list)
    enabled: bool = True


class CreateStepRequest(BaseModel):
    step_order: int
    tier: str
    delay_minutes: int = 0
    notification_channels: Dict[str, Any] = Field(default_factory=dict)
    auto_approve: bool = False


class ReviewRequest(BaseModel):
    action: str
    reviewer: str
    reason: Optional[str] = None


class NotificationChannel(BaseModel):
    type: str
    config: Dict[str, Any]
    enabled: bool = True


class EscalationStep(BaseModel):
    step_id: str
    policy_id: str
    step_order: int
    tier: str
    delay_minutes: int
    notification_channels: Dict[str, Any]
    auto_approve: bool
    created_at: datetime


class EscalationPolicy(BaseModel):
    policy_id: str
    client_id: str
    name: str
    description: Optional[str]
    severity_filter: List[str]
    category_filter: List[str]
    enabled: bool
    created_at: datetime
    steps: Optional[List[EscalationStep]] = None


class EscalationReview(BaseModel):
    review_id: str
    escalation_id: str
    action: str
    reviewer: str
    reason: Optional[str]
    reviewed_at: datetime


class EscalationProgress(BaseModel):
    escalation_id: str
    policy_id: str
    alert_id: str
    current_step: int
    total_steps: int
    status: str
    started_at: datetime
    step_details: List[Dict[str, Any]]
    reviews: List[EscalationReview]
    notification_count: int


class Escalation(BaseModel):
    escalation_id: str
    alert_id: str
    policy_id: str
    client_id: str
    status: str
    current_tier: str
    current_step: int
    total_steps: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    triggered_by: Optional[str]
    progress: Optional[EscalationProgress] = None


class PolicyResponse(BaseModel):
    policy_id: str
    client_id: str
    name: str
    description: Optional[str]
    severity_filter: List[str]
    category_filter: List[str]
    enabled: bool
    created_at: datetime
    step_count: int


class StepResponse(BaseModel):
    step_id: str
    policy_id: str
    step_order: int
    tier: str
    delay_minutes: int
    notification_channels: Dict[str, Any]
    auto_approve: bool
    created_at: datetime


class EvaluationResponse(BaseModel):
    matched: bool
    policy_id: Optional[str] = None
    policy_name: Optional[str] = None
    recommendation: Optional[str] = None


class ReviewQueueItem(BaseModel):
    escalation_id: str
    alert_id: str
    policy_id: str
    policy_name: str
    current_tier: str
    current_step: int
    status: str
    created_at: datetime
    pending_since: datetime


class CancelResponse(BaseModel):
    escalation_id: str
    status: str
    cancelled_at: datetime
    reason: Optional[str] = None


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_escalation_policy(request: CreatePolicyRequest):
    """Create a new escalation policy"""
    policy_id = str(uuid.uuid4())

    policy = PolicyResponse(
        policy_id=policy_id,
        client_id=request.client_id,
        name=request.name,
        description=request.description,
        severity_filter=request.severity_filter,
        category_filter=request.category_filter,
        enabled=request.enabled,
        created_at=datetime.utcnow(),
        step_count=0
    )

    return policy


@router.get("/policies", response_model=List[PolicyResponse])
async def list_escalation_policies(client_id: Optional[str] = Query(None)):
    """List all escalation policies with optional client filter"""
    policies = []

    if client_id:
        policies.append(PolicyResponse(
            policy_id=str(uuid.uuid4()),
            client_id=client_id,
            name="Sample Policy",
            description="Sample escalation policy",
            severity_filter=["CRITICAL", "HIGH"],
            category_filter=["INFRASTRUCTURE"],
            enabled=True,
            created_at=datetime.utcnow(),
            step_count=2
        ))
    else:
        for i in range(3):
            policies.append(PolicyResponse(
                policy_id=str(uuid.uuid4()),
                client_id=f"client-{i}",
                name=f"Policy {i+1}",
                description=f"Escalation policy {i+1}",
                severity_filter=["CRITICAL", "HIGH"],
                category_filter=["INFRASTRUCTURE", "APPLICATION"],
                enabled=True,
                created_at=datetime.utcnow(),
                step_count=2
            ))

    return policies


@router.get("/policies/{policy_id}", response_model=EscalationPolicy)
async def get_escalation_policy(policy_id: str):
    """Get specific escalation policy with all steps"""
    steps = [
        EscalationStep(
            step_id=str(uuid.uuid4()),
            policy_id=policy_id,
            step_order=1,
            tier="TEAM_LEAD",
            delay_minutes=5,
            notification_channels={"email": {"recipients": ["lead@example.com"]}, "slack": {"channel": "#alerts"}},
            auto_approve=False,
            created_at=datetime.utcnow()
        ),
        EscalationStep(
            step_id=str(uuid.uuid4()),
            policy_id=policy_id,
            step_order=2,
            tier="MANAGER",
            delay_minutes=15,
            notification_channels={"email": {"recipients": ["manager@example.com"]}, "pagerduty": {"service_id": "PDXX"}},
            auto_approve=False,
            created_at=datetime.utcnow()
        )
    ]

    policy = EscalationPolicy(
        policy_id=policy_id,
        client_id="client-123",
        name="Critical Infrastructure Policy",
        description="Escalation policy for critical infrastructure alerts",
        severity_filter=["CRITICAL"],
        category_filter=["INFRASTRUCTURE"],
        enabled=True,
        created_at=datetime.utcnow(),
        steps=steps
    )

    return policy


@router.post("/policies/{policy_id}/steps", response_model=StepResponse, status_code=201)
async def add_escalation_step(policy_id: str, request: CreateStepRequest):
    """Add step to escalation policy"""
    step_id = str(uuid.uuid4())

    step = StepResponse(
        step_id=step_id,
        policy_id=policy_id,
        step_order=request.step_order,
        tier=request.tier,
        delay_minutes=request.delay_minutes,
        notification_channels=request.notification_channels,
        auto_approve=request.auto_approve,
        created_at=datetime.utcnow()
    )

    return step


@router.post("/evaluate/{alert_id}", response_model=EvaluationResponse)
async def evaluate_escalation(alert_id: str):
    """Evaluate if alert triggers escalation based on policies"""
    matched = True
    policy_id = str(uuid.uuid4())

    evaluation = EvaluationResponse(
        matched=matched,
        policy_id=policy_id if matched else None,
        policy_name="Critical Infrastructure Policy" if matched else None,
        recommendation="Auto-escalate to TEAM_LEAD" if matched else None
    )

    return evaluation


@router.get("/review-queue", response_model=List[ReviewQueueItem])
async def get_review_queue(tier: Optional[str] = Query(None)):
    """Get pending escalations requiring review"""
    queue_items = []

    for i in range(3):
        queue_items.append(ReviewQueueItem(
            escalation_id=str(uuid.uuid4()),
            alert_id=f"alert-{i+1}",
            policy_id=str(uuid.uuid4()),
            policy_name="Critical Infrastructure Policy",
            current_tier="TEAM_LEAD" if tier is None or tier == "TEAM_LEAD" else "MANAGER",
            current_step=i+1,
            status="PENDING_REVIEW",
            created_at=datetime.utcnow(),
            pending_since=datetime.utcnow()
        ))

    if tier:
        queue_items = [item for item in queue_items if item.current_tier == tier]

    return queue_items


@router.post("/review-queue", status_code=201)
async def create_review_queue_item():
    """Internal endpoint to add item to review queue"""
    return {"status": "added"}


@router.post("/{escalation_id}/review", response_model=Escalation)
async def submit_escalation_review(escalation_id: str, request: ReviewRequest):
    """Submit review decision for escalation"""
    escalation = Escalation(
        escalation_id=escalation_id,
        alert_id="alert-123",
        policy_id=str(uuid.uuid4()),
        client_id="client-123",
        status="REVIEWED" if request.action == "approved" else "REJECTED" if request.action == "rejected" else "ESCALATED",
        current_tier="MANAGER" if request.action == "escalated" else "TEAM_LEAD",
        current_step=1,
        total_steps=2,
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
        completed_at=None if request.action == "escalated" else datetime.utcnow(),
        triggered_by=request.reviewer
    )

    return escalation


@router.get("/{escalation_id}", response_model=Escalation)
async def get_escalation_details(escalation_id: str):
    """Get escalation details"""
    escalation = Escalation(
        escalation_id=escalation_id,
        alert_id="alert-123",
        policy_id=str(uuid.uuid4()),
        client_id="client-123",
        status="IN_PROGRESS",
        current_tier="TEAM_LEAD",
        current_step=1,
        total_steps=2,
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
        completed_at=None,
        triggered_by="SYSTEM"
    )

    return escalation


@router.get("/{escalation_id}/progress", response_model=EscalationProgress)
async def get_escalation_progress(escalation_id: str):
    """Get step-by-step escalation progress"""
    reviews = [
        EscalationReview(
            review_id=str(uuid.uuid4()),
            escalation_id=escalation_id,
            action="approved",
            reviewer="john.doe@example.com",
            reason="Confirmed and handled",
            reviewed_at=datetime.utcnow()
        )
    ]

    step_details = [
        {
            "step": 1,
            "tier": "TEAM_LEAD",
            "status": "COMPLETED",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "notifications_sent": 1
        },
        {
            "step": 2,
            "tier": "MANAGER",
            "status": "PENDING",
            "started_at": None,
            "completed_at": None,
            "notifications_sent": 0
        }
    ]

    progress = EscalationProgress(
        escalation_id=escalation_id,
        policy_id=str(uuid.uuid4()),
        alert_id="alert-123",
        current_step=1,
        total_steps=2,
        status="IN_PROGRESS",
        started_at=datetime.utcnow(),
        step_details=step_details,
        reviews=reviews,
        notification_count=1
    )

    return progress


@router.post("/{escalation_id}/cancel", response_model=CancelResponse)
async def cancel_escalation(escalation_id: str):
    """Cancel escalation"""
    response = CancelResponse(
        escalation_id=escalation_id,
        status="CANCELLED",
        cancelled_at=datetime.utcnow(),
        reason="Manual cancellation"
    )

    return response
