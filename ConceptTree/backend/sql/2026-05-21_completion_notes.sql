-- Phase 3: Completion notes storage
CREATE TABLE IF NOT EXISTS completion_notes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL,
  node_id     TEXT NOT NULL,
  session_id  UUID NOT NULL REFERENCES deep_learn_sessions(id),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_completion_notes_session
  ON completion_notes(session_id);

-- Extend the state constraint to include GENERATING_NOTE
ALTER TABLE deep_learn_sessions
  DROP CONSTRAINT IF EXISTS dl_sessions_state_check;

ALTER TABLE deep_learn_sessions
  ADD CONSTRAINT dl_sessions_state_check CHECK (state IN (
    'INITIALIZING','TEACHING','QUESTIONING','EVALUATING','AWAITING_COMMAND',
    'AI_ASSESSING_READINESS','CONFIRMING_TEST','TESTING','EVALUATING_TEST',
    'CHOOSING_AFTER_FAIL','GENERATING_NOTE','COMPLETED'
  ));
