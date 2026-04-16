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

-- ─── Sprint 2 迁移：F1/F3 新增字段 ───────────────────────────────────────────
-- 学习目的（explore=了解领域 / apply=项目能用 / master=系统精通）
ALTER TABLE plans ADD COLUMN IF NOT EXISTS learning_purpose TEXT DEFAULT 'apply';

-- 节点阶段分组（地基/核心/应用等）
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS phase TEXT;
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS phase_order INTEGER DEFAULT 0;

-- 节点内容深度等级（1-4，由 learning_purpose 决定）
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS depth_level INTEGER DEFAULT 2;

-- 各层内容缓存（避免重复调用 LLM），格式：{"1": "...", "2": "..."}
ALTER TABLE nodes ADD COLUMN IF NOT EXISTS content_cache JSONB DEFAULT '{}'::jsonb;

-- Sprint DB Security: lock down public schema tables behind RLS.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE plans FORCE ROW LEVEL SECURITY;
ALTER TABLE nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE edges FORCE ROW LEVEL SECURITY;
ALTER TABLE learning_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE notes FORCE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes FROM PUBLIC;

DO $$
BEGIN
  IF to_regrole('anon') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes FROM anon';
  END IF;

  IF to_regrole('authenticated') IS NOT NULL THEN
    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE users, user_profiles, plans, nodes, edges, learning_sessions, notes FROM authenticated';
  END IF;
END
$$;
