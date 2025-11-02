-- Migration: 016_lifecycle_enhancements.sql
-- Purpose: Add lifecycle status tracking to alerts table and create supporting views
-- Date: 2025-11-01

-- Add status column to alerts table
ALTER TABLE superops.alerts
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'new';

-- Create status enum type for validation
DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM ('new', 'investigating', 'resolved', 'closed', 'reopened');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create view for current alert status (most recent lifecycle entry per alert)
CREATE OR REPLACE VIEW superops.alert_current_status AS
SELECT DISTINCT ON (alert_id)
    alert_id,
    state as status,
    assigned_to,
    metadata,
    transitioned_by,
    transitioned_at
FROM superops.alert_lifecycle
ORDER BY alert_id, transitioned_at DESC;

-- Add index on alerts.status for performance
CREATE INDEX IF NOT EXISTS idx_alerts_status ON superops.alerts(status);

-- Add composite index for common queries
CREATE INDEX IF NOT EXISTS idx_alerts_status_created ON superops.alerts(status, created_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN superops.alerts.status IS 'Current lifecycle status: new, investigating, resolved, closed, reopened';
COMMENT ON VIEW superops.alert_current_status IS 'View showing current lifecycle status for each alert (most recent transition)';
COMMENT ON TABLE superops.alert_lifecycle IS 'Complete audit trail of alert state transitions';

-- Create index on lifecycle for faster current status lookups
CREATE INDEX IF NOT EXISTS idx_alert_lifecycle_alert_id_time
ON superops.alert_lifecycle(alert_id, transitioned_at DESC);

-- Migration complete
-- Changes:
--   1. Added status column to alerts table
--   2. Created alert_status enum type
--   3. Created alert_current_status view
--   4. Added performance indexes
--   5. Added documentation comments
