-- Move runtime schema changes out of request handlers.
-- This migration is safe to run repeatedly before deploying the runtime DDL cleanup.

ALTER TABLE plans ADD COLUMN IF NOT EXISTS learning_purpose TEXT DEFAULT 'apply';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS target_end_date TIMESTAMPTZ;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS study_frequency TEXT DEFAULT 'flexible';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS study_days_per_week INTEGER DEFAULT 3;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_time TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_timezone TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS archived_reason TEXT;

ALTER TABLE nodes ADD COLUMN IF NOT EXISTS phase TEXT;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS phase_order INTEGER DEFAULT 0;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS depth_level INTEGER DEFAULT 2;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS content_cache JSONB DEFAULT '{}'::jsonb;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS resource_search_cache JSONB DEFAULT '{}'::jsonb;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS target_end_date TIMESTAMPTZ;

ALTER TABLE plans DROP CONSTRAINT IF EXISTS plans_status_check;
ALTER TABLE plans
  ADD CONSTRAINT plans_status_check
  CHECK (status IN ('active', 'paused', 'archived'));

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  response JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_user_created
ON idempotency_keys(user_id, created_at DESC);

ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE idempotency_keys FROM PUBLIC;

DO $$
BEGIN
  IF to_regrole('anon') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE idempotency_keys FROM anon';
  END IF;

  IF to_regrole('authenticated') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE idempotency_keys FROM authenticated';
  END IF;
END
$$;
