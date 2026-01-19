# 数据库架构设计文档

**创建时间**: 2026-01-19  
**状态**: ✅ 已实现  
**当前数据库**: SQLite  
**支持数据库**: SQLite, Supabase (预留)

---

## 📋 概述

项目采用**数据库适配器模式**，支持灵活切换数据库后端，无需修改业务逻辑代码。

### 支持的数据库

| 数据库 | 状态 | 用途 | 优势 |
|--------|------|------|------|
| **SQLite** | ✅ 已实现 | 本地开发 | 零配置、快速、轻量 |
| **Supabase** | 🔄 模板就绪 | 生产环境 | PostgreSQL、实时订阅、认证集成 |

---

## 🏗️ 架构图

```
┌────────────────────────────────────────────────┐
│         Application Layer                      │
│    (routers/auth.py, routers/user.py, etc)    │
└────────────────┬───────────────────────────────┘
                 │
                 ↓ 使用抽象接口
┌────────────────────────────────────────────────┐
│      DatabaseAdapter (Abstract Interface)      │
│  定义所有数据库操作：create_user, get_plan等  │
└────────────────┬───────────────────────────────┘
                 │
         ┌───────┴────────┐
         ↓                ↓
┌─────────────────┐  ┌─────────────────┐
│  SQLiteAdapter  │  │ SupabaseAdapter │
│   (已实现)      │  │   (模板就绪)    │
│                 │  │                 │
│  - SQLite3 API  │  │  - Supabase SDK │
│  - 本地文件存储 │  │  - PostgreSQL   │
└─────────────────┘  └─────────────────┘
```

---

## 📁 文件结构

```
backend/
├── adapters/                      # 数据库适配器包
│   ├── __init__.py               # 导出接口
│   ├── base.py                   # 抽象接口定义
│   ├── sqlite.py                 # SQLite 实现 ✅
│   ├── supabase.py               # Supabase 模板 🔄
│   └── factory.py                # 工厂函数
│
├── config.py                      # 配置管理
├── .env.example                   # 环境变量模板
│
├── DATABASE_MIGRATION_DESIGN.md   # 迁移设计文档
├── SUPABASE_MIGRATION_GUIDE.md    # Supabase 迁移指南
└── DATABASE_ARCHITECTURE.md       # 本文档
```

---

## 🚀 快速开始

### 1. 当前使用 SQLite（默认）

无需任何配置，直接使用：

```python
from adapters import get_database_adapter

# 获取数据库适配器（自动使用 SQLite）
db = get_database_adapter()

# 初始化数据库
db.init_database()

# 使用数据库操作
user = db.get_user_by_email("test@example.com")
```

### 2. 配置文件方式

创建 `.env` 文件：
```bash
DB_TYPE=sqlite
SQLITE_PATH=./database.sqlite
```

然后：
```python
from config import get_database_config
from adapters import get_database_adapter

# 从配置加载
config = get_database_config()
db = get_database_adapter(**config)
```

---

## 🔄 切换到 Supabase

### 步骤 1: 准备工作

1. **创建 Supabase 项目**
   - 访问 https://app.supabase.com
   - 创建新项目
   - 获取 URL 和 API keys

2. **创建数据库表结构**
   - 在 Supabase SQL 编辑器中执行建表 SQL
   - 参考 `SUPABASE_MIGRATION_GUIDE.md`

3. **安装 Supabase SDK**
   ```bash
   pip install supabase
   ```

### 步骤 2: 实现适配器

编辑 `adapters/supabase.py`，实现所有标记为 `TODO` 的方法。

示例：
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
        return response.data[0] if response.data else None
    
    # 实现其他方法...
```

### 步骤 3: 修改配置

更新 `.env`：
```bash
DB_TYPE=supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

### 步骤 4: 启动服务

```bash
# 无需修改任何业务代码，直接启动
python -m uvicorn main:app --reload
```

---

## 💡 API 使用示例

### 用户管理

```python
from adapters import get_database_adapter

db = get_database_adapter()

# 创建用户
user = db.create_user(
    user_id="u_123",
    email="test@example.com",
    password_hash="hashed_password"
)

# 查询用户
user = db.get_user_by_email("test@example.com")
user = db.get_user_by_id("u_123")
```

### 用户画像

```python
# 创建画像
profile = db.create_user_profile(
    profile_id="p_123",
    user_id="u_123",
    occupation="学生",
    programming_level="入门"
)

# 获取画像
profile = db.get_user_profile("u_123")

# 更新画像
updated = db.update_user_profile("u_123", {
    "occupation": "大四学生",
    "abilities": ["Python", "JavaScript"]
})
```

### 学习计划

```python
# 创建计划
plan = db.create_plan({
    "id": "plan_123",
    "user_id": "u_123",
    "title": "学习深度学习",
    "status": "active"
})

# 查询计划
plan = db.get_plan("plan_123")
plans = db.list_user_plans("u_123")

# 更新计划
db.update_plan("plan_123", {"progress": 5})

# 删除计划
db.delete_plan("plan_123")
```

---

## 🧪 测试

### 单元测试

```python
# tests/test_adapters.py
import pytest
from adapters import get_database_adapter

@pytest.fixture
def db():
    """测试夹具"""
    return get_database_adapter(db_type="sqlite", database_path=":memory:")

def test_create_user(db):
    user = db.create_user("u_test", "test@example.com", "hash123")
    assert user["email"] == "test@example.com"

def test_get_user_by_email(db):
    db.create_user("u_test", "test@example.com", "hash123")
    user = db.get_user_by_email("test@example.com")
    assert user is not None
```

### 集成测试

```bash
# 测试 SQLite
DB_TYPE=sqlite pytest tests/

# 测试 Supabase（未来）
DB_TYPE=supabase pytest tests/
```

---

## 📊 性能对比

| 操作 | SQLite | Supabase PostgreSQL |
|------|--------|---------------------|
| 读取单条 | ~0.1ms | ~10ms (网络) |
| 写入单条 | ~0.5ms | ~15ms (网络) |
| 批量查询 | 快速 | 中等（网络延迟）|
| 并发支持 | 低 | 高 |
| 适用场景 | 本地开发、单用户 | 生产环境、多用户 |

---

## 🔐 安全考虑

### SQLite
- ✅ 本地文件，无网络暴露
- ⚠️ 文件权限需注意
- ⚠️ 无用户隔离

### Supabase
- ✅ Row Level Security (RLS)
- ✅ 用户级权限控制
- ✅ 自动备份
- ⚠️ 需要正确配置 RLS 策略

---

## 🎯 最佳实践

### 1. 使用工厂函数

```python
# ✅ 推荐
from adapters import get_database_adapter
db = get_database_adapter()

# ❌ 不推荐
from adapters.sqlite import SQLiteAdapter
db = SQLiteAdapter()  # 耦合到具体实现
```

### 2. 依赖注入

```python
from fastapi import Depends
from adapters import get_database_adapter

def get_db():
    return get_database_adapter()

@router.post("/users")
def create_user(db = Depends(get_db)):
    user = db.create_user(...)
    return user
```

### 3. 错误处理

```python
try:
    user = db.get_user_by_email(email)
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Database error")
```

---

## 📝 迁移检查清单

### 准备 Supabase
- [ ] 创建 Supabase 项目
- [ ] 获取 URL 和 keys
- [ ] 在 SQL 编辑器中创建表结构
- [ ] 配置 Row Level Security 策略
- [ ] 安装 `supabase` Python 包

### 实现适配器
- [ ] 编辑 `adapters/supabase.py`
- [ ] 实现所有抽象方法
- [ ] 处理 JSON 字段（JSONB）
- [ ] 测试每个方法

### 数据迁移
- [ ] 备份 SQLite 数据
- [ ] 编写数据迁移脚本
- [ ] 验证数据完整性
- [ ] 测试所有 API 接口

### 部署
- [ ] 更新 `.env` 配置
- [ ] 重启服务
- [ ] 监控错误日志
- [ ] 性能测试

---

## 🆘 故障排除

### 问题: 切换到 Supabase 后接口报错

**解决**: 
1. 检查 `.env` 配置是否正确
2. 验证 Supabase 表结构是否创建
3. 检查 service_role key 是否正确
4. 查看后端日志定位具体错误

### 问题: Supabase 连接超时

**解决**:
1. 检查网络连接
2. 验证 Supabase URL 是否正确
3. 检查防火墙设置
4. 尝试增加超时时间

---

## 📚 参考资源

### 内部文档
- `DATABASE_MIGRATION_DESIGN.md` - 架构设计
- `SUPABASE_MIGRATION_GUIDE.md` - 详细迁移步骤
- `adapters/supabase.py` - 实现模板

### 外部资源
- [Supabase 官方文档](https://supabase.com/docs)
- [Supabase Python SDK](https://github.com/supabase-community/supabase-py)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

---

## ✅ 总结

当前项目已经具备：
1. ✅ **灵活的数据库架构** - 适配器模式
2. ✅ **SQLite 实现** - 开箱即用
3. ✅ **Supabase 模板** - 随时可切换
4. ✅ **完整文档** - 迁移指南
5. ✅ **零业务代码修改** - 透明切换

**下一步行动**：
- 继续使用 SQLite 进行开发 ✅
- 需要时按照 `SUPABASE_MIGRATION_GUIDE.md` 迁移到 Supabase 🔄
