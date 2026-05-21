CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  occupation TEXT,
  education TEXT,
  programming_level TEXT DEFAULT '入门',
  math_level TEXT DEFAULT '入门',
  abilities JSONB DEFAULT '[]'::jsonb,
  mastered_knowledge JSONB DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  original_input TEXT,
  target_node_id TEXT,
  progress INTEGER DEFAULT 0,
  total INTEGER DEFAULT 0,
  status TEXT DEFAULT 'active',
  last_access_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'unlearned',
  x DOUBLE PRECISION DEFAULT 0,
  y DOUBLE PRECISION DEFAULT 0,
  why TEXT,
  what JSONB DEFAULT '[]'::jsonb,
  mastery JSONB DEFAULT '[]'::jsonb,
  prompt TEXT,
  resources JSONB DEFAULT '[]'::jsonb,
  is_target BOOLEAN DEFAULT FALSE,
  domain TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS edges (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  from_node_id TEXT NOT NULL,
  to_node_id TEXT NOT NULL,
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
  FOREIGN KEY (from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
  FOREIGN KEY (to_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
  UNIQUE(plan_id, from_node_id, to_node_id)
);

CREATE TABLE IF NOT EXISTS learning_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  node_name TEXT,
  action TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
  FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

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

CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
  FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  response JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plans_user_status_access
ON plans(user_id, status, last_access_at DESC);

CREATE INDEX IF NOT EXISTS idx_nodes_plan_status
ON nodes(plan_id, status);

CREATE INDEX IF NOT EXISTS idx_edges_plan
ON edges(plan_id);

CREATE INDEX IF NOT EXISTS idx_notes_user_plan_created
ON notes(user_id, plan_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_learning_sessions_user_created
ON learning_sessions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deep_learn_sessions_user_node_status
ON deep_learn_sessions(user_id, node_id, status);

CREATE INDEX IF NOT EXISTS idx_deep_learn_sessions_user_updated
ON deep_learn_sessions(user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_user_created
ON idempotency_keys(user_id, created_at DESC);

-- ─── Sprint 2 迁移：F1/F3 新增字段 ───────────────────────────────────────────
-- 学习目的（explore=了解领域 / apply=项目能用 / master=系统精通）
ALTER TABLE plans ADD COLUMN IF NOT EXISTS learning_purpose TEXT DEFAULT 'apply';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS target_end_date TIMESTAMPTZ;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS study_frequency TEXT DEFAULT 'flexible';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS study_days_per_week INTEGER DEFAULT 3;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_time TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_timezone TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS archived_reason TEXT;
ALTER TABLE plans DROP CONSTRAINT IF EXISTS plans_status_check;
ALTER TABLE plans
  ADD CONSTRAINT plans_status_check
  CHECK (status IN ('active', 'paused', 'archived'));

-- 节点阶段分组（地基/核心/应用等）
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS phase TEXT;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS phase_order INTEGER DEFAULT 0;

-- 节点内容深度等级（1-4，由 learning_purpose 决定）
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS depth_level INTEGER DEFAULT 2;

-- 各层内容缓存（避免重复调用 LLM），格式：{"1": "...", "2": "..."}
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS content_cache JSONB DEFAULT '{}'::jsonb;

-- 节点扩展资源缓存（用于“搜索更多资源”持久化）
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS resource_search_cache JSONB DEFAULT '{}'::jsonb;

-- 节点级目标完成日期，用于今日提醒和单节点节奏管理。
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS target_end_date TIMESTAMPTZ;

-- Sprint DB Security: lock down public schema tables behind RLS.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_learn_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE plans FORCE ROW LEVEL SECURITY;
ALTER TABLE nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE edges FORCE ROW LEVEL SECURITY;
ALTER TABLE learning_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE deep_learn_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE notes FORCE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes, idempotency_keys FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE deep_learn_sessions FROM PUBLIC;

DO $$
BEGIN
  IF to_regrole('anon') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes, idempotency_keys FROM anon';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE deep_learn_sessions FROM anon';
  END IF;

  IF to_regrole('authenticated') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes, idempotency_keys FROM authenticated';
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE deep_learn_sessions FROM authenticated';
  END IF;
END
$$;
