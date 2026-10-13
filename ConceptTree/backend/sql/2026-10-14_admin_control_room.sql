-- Admin control room foundation.
-- Safe to run repeatedly on existing PostgreSQL/Supabase databases.

CREATE TABLE IF NOT EXISTS user_roles (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  granted_by TEXT REFERENCES users(id) ON DELETE SET NULL,
  PRIMARY KEY (user_id, role),
  CONSTRAINT user_roles_role_check CHECK (role IN ('admin'))
);

CREATE TABLE IF NOT EXISTS session_trace_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL REFERENCES deep_learn_sessions(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  request_id TEXT,
  event_type TEXT NOT NULL,
  event_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ok',
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_ms DOUBLE PRECISION,
  provider TEXT,
  model TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  estimated_cost_usd NUMERIC(14, 6),
  retry_count INTEGER NOT NULL DEFAULT 0,
  error_code TEXT,
  attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
  redacted_input TEXT,
  redacted_output TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  request_id TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_roles_role_user
  ON user_roles(role, user_id);

CREATE INDEX IF NOT EXISTS idx_trace_events_session_created
  ON session_trace_events(session_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_trace_events_user_created
  ON session_trace_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trace_events_type_created
  ON session_trace_events(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_actor_created
  ON admin_audit_logs(admin_user_id, created_at DESC);

ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_trace_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_logs ENABLE ROW LEVEL SECURITY;

ALTER TABLE user_roles FORCE ROW LEVEL SECURITY;
ALTER TABLE session_trace_events FORCE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_logs FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE user_roles FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE session_trace_events FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE admin_audit_logs FROM PUBLIC;

DO $$
BEGIN
  IF to_regrole('anon') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE user_roles FROM anon';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE session_trace_events FROM anon';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE admin_audit_logs FROM anon';
  END IF;

  IF to_regrole('authenticated') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE user_roles FROM authenticated';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE session_trace_events FROM authenticated';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE admin_audit_logs FROM authenticated';
  END IF;
END
$$;
