-- Migration: Fix action_logs.alert_id type mismatch
-- Change alert_id from UUID to VARCHAR to match alert_id format from alerts table
-- Date: 2025-11-02

BEGIN;

-- Step 1: Drop existing index (will recreate after)
DROP INDEX IF EXISTS audit.idx_action_logs_alert_id;

-- Step 2: Alter column type from UUID to VARCHAR(255)
ALTER TABLE audit.action_logs
    ALTER COLUMN alert_id TYPE VARCHAR(255) USING alert_id::VARCHAR;

-- Step 3: Recreate index
CREATE INDEX idx_action_logs_alert_id ON audit.action_logs(alert_id);

-- Step 4: Verify change
DO $$
DECLARE
    col_type text;
BEGIN
    SELECT data_type INTO col_type
    FROM information_schema.columns
    WHERE table_schema = 'audit'
      AND table_name = 'action_logs'
      AND column_name = 'alert_id';

    IF col_type = 'character varying' THEN
        RAISE NOTICE 'SUCCESS: alert_id type changed to VARCHAR';
    ELSE
        RAISE EXCEPTION 'FAILED: alert_id type is still %', col_type;
    END IF;
END $$;

COMMIT;
