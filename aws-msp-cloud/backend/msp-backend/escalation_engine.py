import logging
from typing import Optional, List, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class EscalationEngine:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def evaluate_alert(self, alert_id: str) -> Optional[str]:
        """
        Check if alert matches any enabled escalation policies.
        Returns policy_id if match found, None otherwise.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Fetch alert details
                alert = await conn.fetchrow(
                    """
                    SELECT client_id, severity, category
                    FROM superops.alerts
                    WHERE id = $1
                    """,
                    alert_id
                )

                if not alert:
                    logger.warning(f"Alert {alert_id} not found")
                    return None

                # Find matching policies
                policies = await conn.fetch(
                    """
                    SELECT id, severity_filter, category_filter
                    FROM superops.escalation_policies
                    WHERE enabled = true
                    AND client_id = $1
                    """,
                    alert['client_id']
                )

                for policy in policies:
                    # Check severity filter
                    if policy['severity_filter']:
                        severity_list = json.loads(policy['severity_filter'])
                        if alert['severity'] not in severity_list:
                            continue

                    # Check category filter
                    if policy['category_filter']:
                        category_list = json.loads(policy['category_filter'])
                        if alert['category'] not in category_list:
                            continue

                    logger.info(f"Alert {alert_id} matches policy {policy['id']}")
                    return policy['id']

                logger.info(f"Alert {alert_id} does not match any policies")
                return None

        except Exception as e:
            logger.error(f"Error evaluating alert {alert_id}: {e}")
            raise

    async def create_escalation(self, alert_id: str, policy_id: str) -> str:
        """
        Start escalation workflow for alert.
        Returns escalation_id.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get policy details
                policy = await conn.fetchrow(
                    """
                    SELECT id, name, steps
                    FROM superops.escalation_policies
                    WHERE id = $1
                    """,
                    policy_id
                )

                if not policy:
                    raise ValueError(f"Policy {policy_id} not found")

                # Create escalation
                escalation_id = await conn.fetchval(
                    """
                    INSERT INTO superops.escalations
                    (alert_id, policy_id, status, current_step, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    alert_id,
                    policy_id,
                    'pending',
                    1,
                    datetime.utcnow(),
                    datetime.utcnow()
                )

                logger.info(f"Created escalation {escalation_id} for alert {alert_id}")
                return escalation_id

        except Exception as e:
            logger.error(f"Error creating escalation for alert {alert_id}: {e}")
            raise

    async def process_step(self, escalation_id: str):
        """
        Execute current escalation step:
        1. Get current step details
        2. Check if auto_approve
        3. Send notifications to all channels
        4. Update escalation status to 'in_progress'
        5. If auto_approve, advance to next step
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get escalation
                escalation = await conn.fetchrow(
                    """
                    SELECT id, alert_id, policy_id, current_step, status
                    FROM superops.escalations
                    WHERE id = $1
                    """,
                    escalation_id
                )

                if not escalation:
                    raise ValueError(f"Escalation {escalation_id} not found")

                # Get step details
                step = await conn.fetchrow(
                    """
                    SELECT id, step_number, name, auto_approve, notifications
                    FROM superops.escalation_steps
                    WHERE policy_id = $1 AND step_number = $2
                    """,
                    escalation['policy_id'],
                    escalation['current_step']
                )

                if not step:
                    logger.warning(
                        f"Step {escalation['current_step']} not found for policy {escalation['policy_id']}"
                    )
                    return

                # Update escalation status to in_progress
                await conn.execute(
                    """
                    UPDATE superops.escalations
                    SET status = $1, updated_at = $2
                    WHERE id = $3
                    """,
                    'in_progress',
                    datetime.utcnow(),
                    escalation_id
                )

                # Send notifications
                notifications = json.loads(step['notifications']) if step['notifications'] else []
                for notif in notifications:
                    await self.send_notification(
                        escalation_id,
                        step['id'],
                        notif.get('channel'),
                        notif.get('recipient')
                    )

                # If auto_approve, advance to next step
                if step['auto_approve']:
                    await self.advance_to_next_step(escalation_id)

                logger.info(f"Processed step {step['step_number']} for escalation {escalation_id}")

        except Exception as e:
            logger.error(f"Error processing step for escalation {escalation_id}: {e}")
            raise

    async def review_escalation(
        self,
        escalation_id: str,
        action: str,
        reviewer: str,
        reason: Optional[str] = None
    ):
        """
        Handle human review action:
        - If approved: advance to next step or complete
        - If rejected: mark escalation as rejected, complete
        - If escalated: force advance to next step
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get escalation
                escalation = await conn.fetchrow(
                    """
                    SELECT id, policy_id, current_step, status
                    FROM superops.escalations
                    WHERE id = $1
                    """,
                    escalation_id
                )

                if not escalation:
                    raise ValueError(f"Escalation {escalation_id} not found")

                # Record review
                await conn.execute(
                    """
                    INSERT INTO superops.escalation_reviews
                    (escalation_id, action, reviewer, reason, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    escalation_id,
                    action,
                    reviewer,
                    reason,
                    datetime.utcnow()
                )

                # Handle action
                if action == 'approved':
                    # Check if there are more steps
                    next_step = await conn.fetchval(
                        """
                        SELECT COUNT(*)
                        FROM superops.escalation_steps
                        WHERE policy_id = $1 AND step_number > $2
                        """,
                        escalation['policy_id'],
                        escalation['current_step']
                    )

                    if next_step > 0:
                        await self.advance_to_next_step(escalation_id)
                    else:
                        await self.complete_escalation(escalation_id, 'completed')

                elif action == 'rejected':
                    await self.complete_escalation(escalation_id, 'rejected')

                elif action == 'escalated':
                    await self.advance_to_next_step(escalation_id)

                logger.info(f"Review {action} for escalation {escalation_id} by {reviewer}")

        except Exception as e:
            logger.error(f"Error reviewing escalation {escalation_id}: {e}")
            raise

    async def advance_to_next_step(self, escalation_id: str):
        """
        Move to next tier.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get escalation
                escalation = await conn.fetchrow(
                    """
                    SELECT id, policy_id, current_step
                    FROM superops.escalations
                    WHERE id = $1
                    """,
                    escalation_id
                )

                if not escalation:
                    raise ValueError(f"Escalation {escalation_id} not found")

                # Get next step number
                next_step_number = escalation['current_step'] + 1

                # Check if next step exists
                next_step = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM superops.escalation_steps
                    WHERE policy_id = $1 AND step_number = $2
                    """,
                    escalation['policy_id'],
                    next_step_number
                )

                if next_step == 0:
                    # No more steps, complete escalation
                    await self.complete_escalation(escalation_id, 'completed')
                    return

                # Update current step
                await conn.execute(
                    """
                    UPDATE superops.escalations
                    SET current_step = $1, status = $2, updated_at = $3
                    WHERE id = $4
                    """,
                    next_step_number,
                    'pending',
                    datetime.utcnow(),
                    escalation_id
                )

                # Process new step
                await self.process_step(escalation_id)

                logger.info(f"Advanced escalation {escalation_id} to step {next_step_number}")

        except Exception as e:
            logger.error(f"Error advancing escalation {escalation_id} to next step: {e}")
            raise

    async def complete_escalation(self, escalation_id: str, status: str):
        """
        Mark escalation as done.
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE superops.escalations
                    SET status = $1, completed_at = $2, updated_at = $3
                    WHERE id = $4
                    """,
                    status,
                    datetime.utcnow(),
                    datetime.utcnow(),
                    escalation_id
                )

                logger.info(f"Completed escalation {escalation_id} with status {status}")

        except Exception as e:
            logger.error(f"Error completing escalation {escalation_id}: {e}")
            raise

    async def get_pending_reviews(self, tier: Optional[int] = None) -> List[Dict]:
        """
        Get escalations needing review.
        """
        try:
            async with self.db_pool.acquire() as conn:
                if tier:
                    escalations = await conn.fetch(
                        """
                        SELECT e.id, e.alert_id, e.policy_id, e.current_step,
                               e.status, e.created_at, e.updated_at
                        FROM superops.escalations e
                        WHERE e.status = $1 AND e.current_step = $2
                        ORDER BY e.created_at ASC
                        """,
                        'in_progress',
                        tier
                    )
                else:
                    escalations = await conn.fetch(
                        """
                        SELECT id, alert_id, policy_id, current_step,
                               status, created_at, updated_at
                        FROM superops.escalations
                        WHERE status = $1
                        ORDER BY created_at ASC
                        """,
                        'in_progress'
                    )

                result = []
                for esc in escalations:
                    result.append({
                        'id': str(esc['id']),
                        'alert_id': str(esc['alert_id']),
                        'policy_id': str(esc['policy_id']),
                        'current_step': esc['current_step'],
                        'status': esc['status'],
                        'created_at': esc['created_at'],
                        'updated_at': esc['updated_at']
                    })

                return result

        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            raise

    async def send_notification(
        self,
        escalation_id: str,
        step_id: str,
        channel: str,
        recipient: str
    ):
        """
        Queue notification for delivery.
        Creates entry in escalation_notifications table with status='pending'.
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO superops.escalation_notifications
                    (escalation_id, step_id, channel, recipient, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    escalation_id,
                    step_id,
                    channel,
                    recipient,
                    'pending',
                    datetime.utcnow()
                )

                logger.info(
                    f"Queued {channel} notification to {recipient} for escalation {escalation_id}"
                )

        except Exception as e:
            logger.error(
                f"Error sending notification for escalation {escalation_id}: {e}"
            )
            raise
