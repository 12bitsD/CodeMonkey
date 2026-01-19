# Supabase 迁移指南

**目标**: 将 SQLite 数据库迁移到 Supabase PostgreSQL

---

## 前置准备

### 1. 创建 Supabase 项目

1. 访问 [Supabase](https://app.supabase.com)
2. 点击 "New Project"
3. 填写项目信息：
   - Organization: 选择或创建组织
   - Name: PathFinder（或自定义）
   - Database Password: 设置强密码
   - Region: 选择最近的区域
4. 等待项目创建完成（约2分钟）

### 2. 获取连接信息

在 Supabase Dashboard → Settings → API：
- **Project URL**: `https://xxx.supabase.co`
- **Project API keys**:
  - `anon` key: 用于前端
  - `service_role` key: 用于后端（保密！）

---

## 数据库表结构迁移

### 方法 1: 使用 SQL 编辑器（推荐）

1. 在 Supabase Dashboard → SQL Editor
2. 创建新查询
3. 粘贴以下 SQL：

```sql
-- 1. 用户表
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 用户画像表
CREATE TABLE user_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    occupation TEXT,
    education TEXT,
    programming_level TEXT DEFAULT '入门',
    math_level TEXT DEFAULT '入门',
    abilities JSONB DEFAULT '[]'::jsonb,
    mastered_knowledge JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. 学习计划表
CREATE TABLE plans (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    original_input TEXT,
    target_node_id TEXT,
    progress INTEGER DEFAULT 0,
    total INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    last_access_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 4. 知识节点表
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'unlearned',
    x REAL DEFAULT 0,
    y REAL DEFAULT 0,
    why TEXT,
    what JSONB,
    mastery JSONB,
    prompt TEXT,
    resources JSONB,
    is_target BOOLEAN DEFAULT FALSE,
    domain TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- 5. 边表
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (from_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (to_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
    UNIQUE(plan_id, from_node_id, to_node_id)
);

-- 6. 学习会话表
CREATE TABLE learning_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_name TEXT,
    action TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- 7. 笔记表
CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 8. 创建索引（提升查询性能）
CREATE INDEX idx_plans_user_id ON plans(user_id);
CREATE INDEX idx_nodes_plan_id ON nodes(plan_id);
CREATE INDEX idx_edges_plan_id ON edges(plan_id);
CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_plan_id ON notes(plan_id);

-- 9. 启用 Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

-- 10. 创建 RLS 策略（示例）
-- 用户只能访问自己的数据
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own plans" ON plans
    FOR SELECT USING (auth.uid() = user_id);
```

4. 点击 "Run" 执行

### 方法 2: 使用 Supabase CLI

```bash
# 安装 Supabase CLI
npm install -g supabase

# 登录
supabase login

# 链接项目
supabase link --project-ref your-project-ref

# 应用迁移
supabase db push
```

---

## 代码迁移

### 1. 安装 Supabase Python SDK

```bash
pip install supabase
```

### 2. 实现 Supabase 适配器

编辑 `adapters/supabase.py`，移除所有 `TODO` 和 `raise NotImplementedError`，实现真实逻辑。

参考示例：
```python
from supabase import create_client, Client

class SupabaseAdapter(DatabaseAdapter):
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
    
    def get_user_by_email(self, email: str):
        response = self.client.table("users")\
            .select("*")\
            .eq("email", email)\
            .execute()
        
        if response.data:
            return response.data[0]
        return None
```

### 3. 更新配置

修改 `.env` 文件：
```bash
DB_TYPE=supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

### 4. 更新 `database.py`（可选）

如果想保留 `database.py` 作为入口：
```python
from config import get_database_config
from adapters import get_database_adapter

# 获取适配器
db_config = get_database_config()
db = get_database_adapter(**db_config)

# 使用适配器
def get_user(email: str):
    return db.get_user_by_email(email)
```

---

## 数据迁移

### 创建迁移脚本

```python
# tools/migrate_data.py
import sqlite3
from supabase import create_client

def migrate_users():
    """迁移用户数据"""
    # SQLite
    sqlite_conn = sqlite3.connect('./database.sqlite')
    sqlite_conn.row_factory = sqlite3.Row
    users = sqlite_conn.execute("SELECT * FROM users").fetchall()
    
    # Supabase
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    for user in users:
        supabase.table("users").insert({
            "id": user["id"],
            "email": user["email"],
            "password_hash": user["password_hash"],
            "created_at": user["created_at"]
        }).execute()
    
    print(f"Migrated {len(users)} users")

# 类似地迁移其他表
migrate_users()
migrate_profiles()
migrate_plans()
# ...
```

---

## 认证集成选项

### 选项 1: 继续使用自定义 JWT（当前方案）

保持现有的 JWT 认证，Supabase 只作为数据库使用。

优点：
- 无需修改认证逻辑
- 灵活控制

缺点：
- 无法使用 Supabase Auth 的额外功能

### 选项 2: 使用 Supabase Auth（推荐）

集成 Supabase 的认证系统。

前端修改：
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// 注册
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password123'
})

// 登录
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password123'
})

// 获取当前用户
const { data: { user } } = await supabase.auth.getUser()
```

后端修改：
```python
# 验证 JWT token（Supabase Auth 签发）
from supabase import create_client

supabase = create_client(url, key)
user = supabase.auth.get_user(token)
```

---

## 测试

### 1. 本地测试

```bash
# 确保 .env 配置正确
DB_TYPE=supabase

# 启动服务
python -m uvicorn main:app --reload

# 运行测试
pytest tests/
```

### 2. 验证数据

```bash
# 检查 Supabase 表中的数据
# 在 Supabase Dashboard → Table Editor
```

---

## 性能优化

### 1. 添加索引

在 SQL 编辑器中：
```sql
CREATE INDEX idx_plans_status ON plans(status);
CREATE INDEX idx_nodes_status ON nodes(status);
```

### 2. 使用连接池

```python
# 配置连接池
supabase = create_client(
    url,
    key,
    options={
        'pool_size': 10,
        'max_overflow': 20
    }
)
```

---

## 实时功能（可选）

利用 Supabase 的实时订阅功能：

### 前端订阅

```javascript
// 订阅计划更新
supabase
  .channel('plan-updates')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'plans',
    filter: `id=eq.${planId}`
  }, (payload) => {
    console.log('Plan updated:', payload.new)
  })
  .subscribe()
```

### 后端推送

```python
# 更新数据时自动触发实时推送
db.client.table("plans").update({
    "progress": 5
}).eq("id", plan_id).execute()
```

---

## 回滚计划

如果迁移出现问题，可以快速回滚：

1. 修改 `.env`：`DB_TYPE=sqlite`
2. 重启服务
3. SQLite 数据仍然保留

---

## 检查清单

迁移前：
- [ ] 备份 SQLite 数据库
- [ ] 在 Supabase 创建项目
- [ ] 创建所有表结构
- [ ] 配置 RLS 策略

迁移中：
- [ ] 实现 Supabase 适配器
- [ ] 运行数据迁移脚本
- [ ] 验证数据完整性
- [ ] 测试所有 API 接口

迁移后：
- [ ] 更新生产环境配置
- [ ] 监控性能和错误
- [ ] 设置数据库备份
- [ ] 文档更新

---

## 常见问题

### Q: 是否需要修改前端代码？

A: 不需要。前端仍然通过 API 与后端通信，后端透明地切换数据库。

### Q: Supabase 费用如何？

A: 
- Free tier: 500MB 数据库，50MB 文件存储
- Pro: $25/月，8GB 数据库，100GB 文件存储

### Q: 如何处理 JSON 字段？

A: PostgreSQL 原生支持 JSONB 类型，性能更好：
```python
# SQLite: TEXT + JSON 序列化
abilities = json.loads(row["abilities"])

# PostgreSQL: 直接使用 JSONB
abilities = row["abilities"]  # 已经是 Python 对象
```

---

## 参考资源

- [Supabase 文档](https://supabase.com/docs)
- [Supabase Python SDK](https://github.com/supabase-community/supabase-py)
- [PostgreSQL vs SQLite](https://www.postgresql.org/docs/)
- [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
