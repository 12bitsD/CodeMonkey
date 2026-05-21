-- Deep Learn runtime schema alignment.
-- Safe to run repeatedly on existing Supabase/Postgres databases.

CREATE TABLE IF NOT EXISTS deep_learn_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'INITIALIZING',
  current_concept_index INTEGER NOT NULL DEFAULT 0,
  difficulty_level INTEGER NOT NULL DEFAULT 3,
  wrong_count_current INTEGER NOT NULL DEFAULT 0,
  concepts_status JSONB NOT NULL DEFAULT '{}'::jsonb,
  weak_points JSONB NOT NULL DEFAULT '[]'::jsonb,
  recent_turns JSONB NOT NULL DEFAULT '[]'::jsonb,
  what_list JSONB NOT NULL DEFAULT '[]'::jsonb,
  conversation_summary TEXT,
  test_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
  test_current_index INTEGER NOT NULL DEFAULT 0,
  test_results JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'in_progress',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  ended_at TIMESTAMPTZ,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
  FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

ALTER TABLE deep_learn_sessions ADD COLUMN IF NOT EXISTS test_questions JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE deep_learn_sessions ADD COLUMN IF NOT EXISTS test_current_index INTEGER NOT NULL DEFAULT 0;
ALTER TABLE deep_learn_sessions ADD COLUMN IF NOT EXISTS test_results JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE deep_learn_sessions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_deep_learn_sessions_user_node_status
ON deep_learn_sessions(user_id, node_id, status);

CREATE INDEX IF NOT EXISTS idx_deep_learn_sessions_user_updated
ON deep_learn_sessions(user_id, updated_at DESC);

ALTER TABLE deep_learn_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_learn_sessions FORCE ROW LEVEL SECURITY;
REVOKE ALL PRIVILEGES ON TABLE deep_learn_sessions FROM PUBLIC;

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  response JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
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
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE deep_learn_sessions FROM anon';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE idempotency_keys FROM anon';
  END IF;

  IF to_regrole('authenticated') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE deep_learn_sessions FROM authenticated';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE idempotency_keys FROM authenticated';
  END IF;
END
$$;
