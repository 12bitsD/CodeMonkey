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
