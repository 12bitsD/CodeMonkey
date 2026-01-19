# 数据库迁移到 Supabase 设计文档

**创建时间**: 2026-01-19  
**状态**: 架构设计

---

## 目标

为项目设计一个灵活的数据库抽象层，支持：
1. 当前的 SQLite 实现（开发/本地环境）
2. 未来迁移到 Supabase PostgreSQL（生产环境）
3. 最小化代码改动

---

## 架构设计

### 1. 数据库适配器模式

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│      (routers, services)                │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│      Database Adapter Interface         │
│   (抽象接口，定义所有数据库操作)        │
└─────────────┬───────────────────────────┘
              │
        ┌─────┴─────┐
        ↓           ↓
┌──────────────┐  ┌──────────────┐
│   SQLite     │  │   Supabase   │
│   Adapter    │  │   Adapter    │
└──────────────┘  └──────────────┘
```

### 2. 接口设计

```python
class DatabaseAdapter(ABC):
    """数据库适配器抽象接口"""
    
    @abstractmethod
    async def connect(self):
        """建立数据库连接"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """关闭数据库连接"""
        pass
    
    # 用户相关
    @abstractmethod
    async def create_user(self, user_data: dict) -> dict:
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> dict:
        pass
    
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> dict:
        pass
    
    # 用户画像
    @abstractmethod
    async def create_user_profile(self, profile_data: dict):
        pass
    
    @abstractmethod
    async def get_user_profile(self, user_id: str) -> dict:
        pass
    
    @abstractmethod
    async def update_user_profile(self, user_id: str, updates: dict):
        pass
    
    # 学习计划
    @abstractmethod
    async def create_plan(self, plan_data: dict) -> dict:
        pass
    
    @abstractmethod
    async def get_plan(self, plan_id: str) -> dict:
        pass
    
    @abstractmethod
    async def list_user_plans(self, user_id: str) -> list:
        pass
    
    # ... 其他表的 CRUD 操作
```

---

## 迁移步骤

### Phase 1: 创建抽象层（当前）
- [x] 设计接口
- [ ] 创建 `adapters/` 目录
- [ ] 创建 `base.py` 定义抽象接口
- [ ] 重构现有 SQLite 代码为 `adapters/sqlite.py`
- [ ] 更新所有路由使用适配器

### Phase 2: Supabase 准备（未来）
- [ ] 创建 `adapters/supabase.py`
- [ ] 实现 Supabase 客户端集成
- [ ] 配置环境变量
- [ ] 数据库迁移脚本

### Phase 3: 切换和测试（未来）
- [ ] 配置文件支持 `DB_TYPE` 环境变量
- [ ] 并行测试两种数据库
- [ ] 数据迁移工具
- [ ] 生产环境部署

---

## Supabase 特性

### 优势
1. **实时功能**: 支持数据库订阅
2. **认证集成**: 内置用户认证（可替换当前 JWT）
3. **存储**: 文件存储功能
4. **PostgreSQL**: 功能更强大
5. **自动备份**: 云端备份

### 集成计划
```python
# 未来的 Supabase 配置
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_KEY = "your-anon-key"
SUPABASE_SERVICE_KEY = "your-service-key"

# 认证选项
# Option 1: 继续使用自定义 JWT（当前方案）
# Option 2: 使用 Supabase Auth（推荐）
```

---

## 配置管理

### 环境变量
```bash
# .env
DB_TYPE=sqlite  # 或 supabase
DB_PATH=./database.sqlite  # SQLite 路径

# Supabase 配置（未来）
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-key
```

### config.py 更新
```python
class Settings:
    DB_TYPE: str = "sqlite"  # sqlite | supabase
    
    # SQLite
    SQLITE_PATH: str = "./database.sqlite"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
```

---

## 数据迁移

### 迁移工具设计
```python
# tools/migrate_to_supabase.py
async def migrate_sqlite_to_supabase():
    """将 SQLite 数据迁移到 Supabase"""
    sqlite_adapter = SQLiteAdapter()
    supabase_adapter = SupabaseAdapter()
    
    # 1. 迁移用户
    users = await sqlite_adapter.get_all_users()
    for user in users:
        await supabase_adapter.create_user(user)
    
    # 2. 迁移画像
    # 3. 迁移计划
    # ...
```

---

## 性能考虑

### SQLite (当前)
- **优点**: 
  - 零配置
  - 快速本地访问
  - 适合开发/单用户
- **缺点**: 
  - 并发性能差
  - 不适合多用户生产环境

### Supabase PostgreSQL (未来)
- **优点**: 
  - 高并发支持
  - 强大的 SQL 功能
  - 云端高可用
- **缺点**: 
  - 需要网络连接
  - 额外成本

---

## 测试策略

### 适配器测试
```python
# tests/test_adapters.py
@pytest.fixture
def db_adapter():
    """根据配置返回对应的适配器"""
    if settings.DB_TYPE == "sqlite":
        return SQLiteAdapter()
    elif settings.DB_TYPE == "supabase":
        return SupabaseAdapter()

async def test_create_user(db_adapter):
    """测试创建用户（适配器无关）"""
    user = await db_adapter.create_user({
        "email": "test@example.com",
        "password_hash": "..."
    })
    assert user["email"] == "test@example.com"
```

---

## 参考资料

- [Supabase Python 文档](https://supabase.com/docs/reference/python/introduction)
- [Supabase 认证指南](https://supabase.com/docs/guides/auth)
- [PostgreSQL vs SQLite](https://www.sqlite.org/whentouse.html)

---

## 下一步行动

1. ✅ 完成架构设计
2. 🔄 实现适配器抽象层
3. ⏳ 创建 Supabase 模板代码
4. ⏳ 更新部署文档

