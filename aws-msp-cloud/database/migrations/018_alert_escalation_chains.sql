-- Migration 018: Alert Escalation Chains
-- Purpose: Multi-tier escalation workflow for alert management
-- Created: 2025-11-01
-- Description: Implements escalation policies, steps, tracking, reviews, and notifications

BEGIN;

-- Set search path for convenience
SET search_path TO superops, public;

-- ============================================================================
-- TABLE 1: escalation_policies
-- Description: Define escalation rules and conditions for different alert types
-- ============================================================================

CREATE TABLE IF NOT EXISTS superops.escalation_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES superops.clients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    severity_filter VARCHAR(50)[] DEFAULT '{}',
    category_filter VARCHAR(50)[] DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE superops.escalation_policies IS 'Defines escalation policies with severity and category filters';
COMMENT ON COLUMN superops.escalation_policies.id IS 'Unique identifier for the escalation policy';
COMMENT ON COLUMN superops.escalation_policies.client_id IS 'Reference to the client who owns this policy';
COMMENT ON COLUMN superops.escalation_policies.name IS 'Human-readable name of the escalation policy';
COMMENT ON COLUMN superops.escalation_policies.description IS 'Detailed description of when this policy applies';
COMMENT ON COLUMN superops.escalation_policies.severity_filter IS 'Array of severities to match (e.g., ARRAY[''critical'', ''high''])';
COMMENT ON COLUMN superops.escalation_policies.category_filter IS 'Array of alert categories to match';
COMMENT ON COLUMN superops.escalation_policies.enabled IS 'Whether this policy is active';

CREATE INDEX idx_escalation_policies_client ON superops.escalation_policies(client_id);
CREATE INDEX idx_escalation_policies_enabled ON superops.escalation_policies(enabled);
CREATE INDEX idx_escalation_policies_created_at ON superops.escalation_policies(created_at DESC);

-- ============================================================================
-- TABLE 2: escalation_steps
-- Description: Define the steps/tiers in each escalation policy
-- ============================================================================

CREATE TABLE IF NOT EXISTS superops.escalation_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES superops.escalation_policies(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    tier VARCHAR(50) NOT NULL,
    delay_minutes INTEGER DEFAULT 0,
    notification_channels JSONB DEFAULT '{}',
    auto_approve BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(policy_id, step_order)
);

COMMENT ON TABLE superops.escalation_steps IS 'Individual steps/tiers within an escalation policy';
COMMENT ON COLUMN superops.escalation_steps.id IS 'Unique identifier for the escalation step';
COMMENT ON COLUMN superops.escalation_steps.policy_id IS 'Reference to parent escalation policy';
COMMENT ON COLUMN superops.escalation_steps.step_order IS 'Execution order (1, 2, 3, etc.)';
COMMENT ON COLUMN superops.escalation_steps.tier IS 'Escalation tier (L1, L2, L3, manager)';
COMMENT ON COLUMN superops.escalation_steps.delay_minutes IS 'Minutes to wait before executing this step';
COMMENT ON COLUMN superops.escalation_steps.notification_channels IS 'JSON with email, slack, pagerduty recipients';
COMMENT ON COLUMN superops.escalation_steps.auto_approve IS 'Whether this step auto-approves without review';

CREATE INDEX idx_escalation_steps_policy ON superops.escalation_steps(policy_id);
CREATE INDEX idx_escalation_steps_tier ON superops.escalation_steps(tier);
CREATE INDEX idx_escalation_steps_order ON superops.escalation_steps(policy_id, step_order);

-- ============================================================================
-- TABLE 3: escalations
-- Description: Track individual escalation instances for alerts
-- ============================================================================

CREATE TABLE IF NOT EXISTS superops.escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES superops.alerts(id) ON DELETE CASCADE,
    policy_id UUID NOT NULL REFERENCES superops.escalation_policies(id),
    current_step INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

COMMENT ON TABLE superops.escalations IS 'Individual escalation instances tracking the progression of an alert through escalation steps';
COMMENT ON COLUMN superops.escalations.id IS 'Unique identifier for the escalation instance';
COMMENT ON COLUMN superops.escalations.alert_id IS 'Reference to the alert being escalated';
COMMENT ON COLUMN superops.escalations.policy_id IS 'Reference to the escalation policy being applied';
COMMENT ON COLUMN superops.escalations.current_step IS 'Current step in the escalation process';
COMMENT ON COLUMN superops.escalations.status IS 'Current status: pending, in_progress, approved, rejected, completed, cancelled';
COMMENT ON COLUMN superops.escalations.started_at IS 'When the escalation started';
COMMENT ON COLUMN superops.escalations.completed_at IS 'When the escalation completed or was rejected';
COMMENT ON COLUMN superops.escalations.metadata IS 'Additional context and data (e.g., original alert context)';

CREATE INDEX idx_escalations_alert ON superops.escalations(alert_id);
CREATE INDEX idx_escalations_policy ON superops.escalations(policy_id);
CREATE INDEX idx_escalations_status ON superops.escalations(status);
CREATE INDEX idx_escalations_current_step ON superops.escalations(current_step);
CREATE INDEX idx_escalations_started_at ON superops.escalations(started_at DESC);

-- ============================================================================
-- TABLE 4: escalation_reviews
-- Description: Track review actions at each escalation step
-- ============================================================================

CREATE TABLE IF NOT EXISTS superops.escalation_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escalation_id UUID NOT NULL REFERENCES superops.escalations(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    reviewer VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    reason TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE superops.escalation_reviews IS 'Records of human reviews and approvals at each escalation step';
COMMENT ON COLUMN superops.escalation_reviews.id IS 'Unique identifier for the review record';
COMMENT ON COLUMN superops.escalation_reviews.escalation_id IS 'Reference to the escalation being reviewed';
COMMENT ON COLUMN superops.escalation_reviews.step_order IS 'Which step was reviewed';
COMMENT ON COLUMN superops.escalation_reviews.reviewer IS 'Name or ID of the person who reviewed';
COMMENT ON COLUMN superops.escalation_reviews.action IS 'Action taken: approved, rejected, escalated';
COMMENT ON COLUMN superops.escalation_reviews.reason IS 'Reason for the action (optional)';
COMMENT ON COLUMN superops.escalation_reviews.reviewed_at IS 'When the review occurred';

CREATE INDEX idx_escalation_reviews_escalation ON superops.escalation_reviews(escalation_id);
CREATE INDEX idx_escalation_reviews_step ON superops.escalation_reviews(step_order);
CREATE INDEX idx_escalation_reviews_reviewed_at ON superops.escalation_reviews(reviewed_at DESC);
CREATE INDEX idx_escalation_reviews_action ON superops.escalation_reviews(action);

-- ============================================================================
-- TABLE 5: escalation_notifications
-- Description: Track notification delivery for escalation steps
-- ============================================================================

CREATE TABLE IF NOT EXISTS superops.escalation_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escalation_id UUID NOT NULL REFERENCES superops.escalations(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES superops.escalation_steps(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

COMMENT ON TABLE superops.escalation_notifications IS 'Tracks notification delivery attempts for escalation steps';
COMMENT ON COLUMN superops.escalation_notifications.id IS 'Unique identifier for the notification';
COMMENT ON COLUMN superops.escalation_notifications.escalation_id IS 'Reference to the escalation';
COMMENT ON COLUMN superops.escalation_notifications.step_id IS 'Reference to the escalation step that generated the notification';
COMMENT ON COLUMN superops.escalation_notifications.channel IS 'Notification channel: email, slack, pagerduty';
COMMENT ON COLUMN superops.escalation_notifications.recipient IS 'Destination email, Slack user, or PagerDuty user';
COMMENT ON COLUMN superops.escalation_notifications.status IS 'Delivery status: pending, sent, failed, delivered';
COMMENT ON COLUMN superops.escalation_notifications.sent_at IS 'When notification was sent';
COMMENT ON COLUMN superops.escalation_notifications.delivered_at IS 'When notification was confirmed delivered';
COMMENT ON COLUMN superops.escalation_notifications.error_message IS 'Error details if delivery failed';
COMMENT ON COLUMN superops.escalation_notifications.metadata IS 'Additional data (message ID, response, etc.)';

CREATE INDEX idx_escalation_notifications_escalation ON superops.escalation_notifications(escalation_id);
CREATE INDEX idx_escalation_notifications_step ON superops.escalation_notifications(step_id);
CREATE INDEX idx_escalation_notifications_status ON superops.escalation_notifications(status);
CREATE INDEX idx_escalation_notifications_channel ON superops.escalation_notifications(channel);
CREATE INDEX idx_escalation_notifications_sent_at ON superops.escalation_notifications(sent_at DESC);

-- ============================================================================
-- TRIGGER: Auto-update updated_at on escalation_policies
-- ============================================================================

CREATE OR REPLACE FUNCTION superops.update_escalation_policies_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_update_escalation_policies_timestamp ON superops.escalation_policies;

CREATE TRIGGER tr_update_escalation_policies_timestamp
BEFORE UPDATE ON superops.escalation_policies
FOR EACH ROW
EXECUTE FUNCTION superops.update_escalation_policies_timestamp();

-- ============================================================================
-- VIEW: escalation_queue
-- Description: Active escalations with alert and policy context
-- ============================================================================

CREATE OR REPLACE VIEW superops.escalation_queue AS
SELECT
    e.id AS escalation_id,
    e.alert_id,
    e.policy_id,
    e.current_step,
    e.status,
    e.started_at,
    a.severity,
    a.message AS alert_message,
    ast.asset_name AS asset_name,
    ast.client_id,
    c.client_name AS client_name,
    p.name AS policy_name,
    es.tier AS current_tier,
    es.delay_minutes,
    es.auto_approve,
    COUNT(DISTINCT en.id) AS pending_notifications,
    COUNT(DISTINCT er.id) AS review_count
FROM superops.escalations e
JOIN superops.alerts a ON e.alert_id = a.id
JOIN superops.assets ast ON a.asset_id = ast.id
JOIN superops.clients c ON ast.client_id = c.id
JOIN superops.escalation_policies p ON e.policy_id = p.id
JOIN superops.escalation_steps es ON p.id = es.policy_id AND es.step_order = e.current_step
LEFT JOIN superops.escalation_notifications en ON e.id = en.escalation_id AND en.status = 'pending'
LEFT JOIN superops.escalation_reviews er ON e.id = er.escalation_id
WHERE e.status IN ('pending', 'in_progress')
GROUP BY
    e.id, e.alert_id, e.policy_id, e.current_step, e.status, e.started_at,
    a.severity, a.message, ast.asset_name, ast.client_id, c.client_name, p.name,
    es.tier, es.delay_minutes, es.auto_approve;

COMMENT ON VIEW superops.escalation_queue IS 'Active escalations with alert and policy context for easy querying';

-- ============================================================================
-- FUNCTION: get_pending_escalations(tier VARCHAR)
-- Description: Get escalations awaiting review at a specific tier
-- ============================================================================

CREATE OR REPLACE FUNCTION superops.get_pending_escalations(p_tier VARCHAR DEFAULT NULL)
RETURNS TABLE (
    escalation_id UUID,
    alert_id UUID,
    alert_message TEXT,
    severity VARCHAR,
    client_name VARCHAR,
    asset_name VARCHAR,
    tier VARCHAR,
    delay_minutes INTEGER,
    auto_approve BOOLEAN,
    started_at TIMESTAMP WITH TIME ZONE,
    pending_notifications INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        eq.escalation_id,
        eq.alert_id,
        eq.alert_message,
        eq.severity,
        eq.client_name,
        eq.asset_name,
        eq.current_tier,
        eq.delay_minutes,
        eq.auto_approve,
        eq.started_at,
        eq.pending_notifications
    FROM superops.escalation_queue eq
    WHERE
        eq.status IN ('pending', 'in_progress')
        AND (p_tier IS NULL OR eq.current_tier = p_tier)
        AND NOT eq.auto_approve
    ORDER BY
        eq.started_at ASC,
        eq.severity DESC,
        eq.escalation_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION superops.get_pending_escalations(VARCHAR) IS 'Retrieve escalations awaiting manual review at a specific tier';

-- ============================================================================
-- FUNCTION: escalation_progress(escalation_id UUID)
-- Description: Get escalation progression details
-- ============================================================================

CREATE OR REPLACE FUNCTION superops.escalation_progress(p_escalation_id UUID)
RETURNS TABLE (
    step_order INTEGER,
    tier VARCHAR,
    status VARCHAR,
    delay_minutes INTEGER,
    auto_approve BOOLEAN,
    notification_count INTEGER,
    review_count INTEGER,
    last_review_action VARCHAR,
    last_review_time TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        es.step_order,
        es.tier,
        CASE
            WHEN e.completed_at IS NOT NULL THEN 'completed'
            WHEN e.current_step = es.step_order THEN e.status
            ELSE 'skipped'
        END AS status,
        es.delay_minutes,
        es.auto_approve,
        COALESCE(COUNT(DISTINCT en.id), 0)::INTEGER,
        COALESCE(COUNT(DISTINCT er.id), 0)::INTEGER,
        (SELECT action FROM superops.escalation_reviews WHERE escalation_id = p_escalation_id ORDER BY reviewed_at DESC LIMIT 1),
        (SELECT reviewed_at FROM superops.escalation_reviews WHERE escalation_id = p_escalation_id ORDER BY reviewed_at DESC LIMIT 1)
    FROM superops.escalations e
    JOIN superops.escalation_policies p ON e.policy_id = p.id
    JOIN superops.escalation_steps es ON p.id = es.policy_id
    LEFT JOIN superops.escalation_notifications en ON e.id = en.escalation_id AND en.step_id = es.id
    LEFT JOIN superops.escalation_reviews er ON e.id = er.escalation_id AND er.step_order = es.step_order
    WHERE e.id = p_escalation_id
    GROUP BY es.step_order, es.tier, es.delay_minutes, es.auto_approve, e.completed_at, e.current_step, e.status
    ORDER BY es.step_order;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION superops.escalation_progress(UUID) IS 'Show progression and details for all steps in an escalation';

-- ============================================================================
-- CONSTRAINTS: Add data validation
-- ============================================================================

ALTER TABLE superops.escalations
ADD CONSTRAINT check_escalation_status CHECK (
    status IN ('pending', 'in_progress', 'approved', 'rejected', 'completed', 'cancelled')
);

ALTER TABLE superops.escalation_reviews
ADD CONSTRAINT check_review_action CHECK (
    action IN ('approved', 'rejected', 'escalated')
);

ALTER TABLE superops.escalation_notifications
ADD CONSTRAINT check_notification_status CHECK (
    status IN ('pending', 'sent', 'failed', 'delivered')
),
ADD CONSTRAINT check_notification_channel CHECK (
    channel IN ('email', 'slack', 'pagerduty')
);

-- ============================================================================
-- GRANTS: Set permissions (adjust schema/user as needed)
-- ============================================================================

GRANT SELECT, INSERT, UPDATE ON superops.escalation_policies TO postgres;
GRANT SELECT, INSERT, UPDATE ON superops.escalation_steps TO postgres;
GRANT SELECT, INSERT, UPDATE ON superops.escalations TO postgres;
GRANT SELECT, INSERT ON superops.escalation_reviews TO postgres;
GRANT SELECT, INSERT, UPDATE ON superops.escalation_notifications TO postgres;
GRANT SELECT ON superops.escalation_queue TO postgres;
GRANT EXECUTE ON FUNCTION superops.get_pending_escalations(VARCHAR) TO postgres;
GRANT EXECUTE ON FUNCTION superops.escalation_progress(UUID) TO postgres;

-- ============================================================================
-- COMMIT TRANSACTION
-- ============================================================================

COMMIT;
