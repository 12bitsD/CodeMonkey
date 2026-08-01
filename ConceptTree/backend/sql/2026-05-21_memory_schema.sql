-- Phase 2 Memory Schema Migration
-- Run this in Supabase SQL Editor

-- Long-term Memory
CREATE TABLE IF NOT EXISTS user_learning_profile (
  user_id           TEXT PRIMARY KEY,
  learning_style    JSONB NOT NULL DEFAULT '{}'::jsonb,
  mastered_concepts JSONB NOT NULL DEFAULT '[]'::jsonb,
  weak_concepts     JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Episodic Memory
CREATE TABLE IF NOT EXISTS learning_session_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             TEXT NOT NULL,
  node_id             TEXT NOT NULL,
  plan_id             TEXT NOT NULL,
  session_id          TEXT NOT NULL REFERENCES deep_learn_sessions(id) ON DELETE CASCADE,
  summary             TEXT,
  concepts_covered    JSONB NOT NULL DEFAULT '[]'::jsonb,
  weak_points         JSONB NOT NULL DEFAULT '[]'::jsonb,
  strong_points       JSONB NOT NULL DEFAULT '[]'::jsonb,
  test_score          REAL,
  passed              BOOLEAN NOT NULL DEFAULT FALSE,
  conversation_turns  INTEGER NOT NULL DEFAULT 0,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lsr_user_node_created
  ON learning_session_records(user_id, node_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lsr_user_passed
  ON learning_session_records(user_id, passed);

-- Procedural Memory
CREATE TABLE IF NOT EXISTS teaching_patterns (
  user_id       TEXT NOT NULL,
  pattern_key   TEXT NOT NULL,
  pattern_value TEXT NOT NULL,
  confidence    REAL NOT NULL DEFAULT 0.5,
  sample_count  INTEGER NOT NULL DEFAULT 1,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, pattern_key),
  CONSTRAINT tp_pattern_key_check CHECK (pattern_key IN (
    'effective_analogy_type','optimal_question_density',
    'preferred_explanation_order','common_misconception_pattern','ideal_pace'
  ))
);

-- Storage RLS Policy (run in Supabase Dashboard)
-- CREATE POLICY "users can upload own images" ON storage.objects
--   FOR INSERT TO authenticated
--   WITH CHECK (bucket_id = 'deep_learn_images' AND (storage.foldername(name))[1] = auth.uid()::text);
