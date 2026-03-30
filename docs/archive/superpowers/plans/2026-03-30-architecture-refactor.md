# ConceptTree 架构重构实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.

**Goal:** 采用 bitsNovels 架构模式，重构文档体系和代码组织，提升 AI Agent 协作效率

**Architecture:** 
- 文档层：4 文件任务包 (epic-N/{be.md, fe.md, contract.md}) + AGENTS.md + DoD
- 代码层：按 Epic 模块化 (epic_N/models.py) + 测试按 Epic 组织
- 清理层：删除冗余文档 (archive/, 进度总览.md) 和单体 models.py

**Tech Stack:** Python/FastAPI (backend), React (frontend), pytest (testing)

---

## Chunk 1: 文档结构重组

### Task 1: 创建顶层文档

**Files:**
- Create: `docs/spec/AGENTS.md`
- Create: `docs/spec/DOD.md`
- Create: `docs/spec/CLAUDE.md`
- Modify: `docs/spec/后端-通用规范.md` (合并入 Epic)

- [ ] **Step 1: 创建 docs/spec/AGENTS.md**

```markdown
# Agent 操作手册

## 快速开始

1. 读 `docs/spec/AGENTS.md` (本文件)
2. 读对应的 Epic spec (`docs/spec/epic-N/`)
3. 照 TDD 流程实现
4. 逐项检查 DoD

## 4 文件任务包

每个 Epic 功能需要读取:

1. `docs/spec/epic-N/be.md` — 后端需求
2. `docs/spec/epic-N/fe.md` — 前端需求  
3. `docs/spec/epic-N/contract.md` — API 契约
4. `docs/design/BACKEND.md` — 架构约束

## TDD 铁律

任何功能必须:
1. 先写红灯测试
2. 实现通过测试
3. 重构

## Epic 索引

| Epic | 功能 | 路由 |
|------|------|------|
| epic-1 | 认证与用户 | /api/auth/*, /api/user/* |
| epic-2 | 图谱核心 | /api/plans/*, /api/plans/{id}/graph |
| epic-3 | 笔记 | /api/notes/* |
| epic-4 | AI 服务 | /api/ai/* |
| epic-5 | 统计 | /api/stats/* |
```

- [ ] **Step 2: 创建 docs/spec/DOD.md**

```markdown
# Definition of Done

## 功能开发

- [ ] 测试覆盖: 新增功能有对应的单元测试
- [ ] API 契约: 请求/响应格式符合 contract.md
- [ ] 错误处理: 错误码符合规范
- [ ] 数据验证: Pydantic validation 通过
- [ ] 边界 case: 空值、越界、重复等已处理

## 代码质量

- [ ] 命名: 函数/变量命名清晰
- [ ] 注释: 复杂逻辑有解释
- [ ] 无硬编码: 配置在环境变量或 config
- [ ] 无裸 except: 捕获具体异常

## 文档更新

- [ ] Epic spec 已更新 (如有必要)
- [ ] API 契约已更新 (如有必要)
- [ ] 类型定义已同步
```

- [ ] **Step 3: 创建 docs/spec/CLAUDE.md** (替换不存在的老文件)

```markdown
# CLAUDE.md — AI Session 入口

> 每次 session 开始先读这个文件。

## 必读文档

| 文档 | 说明 |
|------|------|
| `docs/spec/AGENTS.md` | Agent 操作手册 |
| `docs/spec/DOD.md` | 完成标准 |
| `docs/spec/epic-N/be.md` | 当前 Epic 后端需求 |

## 项目结构

```
ConceptTree/
├── backend/
│   ├── main.py           # FastAPI 入口
│   ├── epic_N/           # 按 Epic 模块化
│   │   ├── models.py     # Epic 相关 Pydantic 模型
│   │   └── utils.py      # Epic 相关工具
│   ├── routers/          # API 路由
│   ├── services/         # 业务逻辑
│   └── tests/            # 测试 (按 epic_N/ 组织)
└── frontend/
    └── src/
```

## 开发规则

1. 写代码前先读 `docs/spec/AGENTS.md`
2. 先更新规范，再写测试，最后实现
3. 测试不通过不提交
4. 在规范中标记实现状态
```

- [ ] **Step 4: Commit**

```bash
git add docs/spec/AGENTS.md docs/spec/DOD.md docs/spec/CLAUDE.md
git commit -m "docs: add AGENTS.md, DOD.md, and CLAUDE.md"
```

---

### Task 2: 创建 Epic Spec 文件

**Files:**
- Create: `docs/spec/epic-1-auth/`
- Create: `docs/spec/epic-2-graph/`
- Create: `docs/spec/epic-3-notes/`
- Create: `docs/spec/epic-4-ai/`
- Create: `docs/spec/epic-5-stats/`

- [ ] **Step 1: 创建 epic-1-auth/be.md**

```markdown
# Epic 1: 认证与用户

## 用户故事

### US-1.1 用户注册
**作为** 访客  
**我想要** 注册账号  
**以便于** 使用学习功能

**验收标准:**
- 邮箱格式正确
- 密码 >= 6 位
- 邮箱不重复
- 返回 JWT token

**API:** `POST /api/auth/register`

### US-1.2 用户登录
**作为** 访客  
**我想要** 登录账号  
**以便** 使用学习功能

**验收标准:**
- 邮箱密码正确
- 返回 JWT token

**API:** `POST /api/auth/login`

### US-1.3 用户登出
**作为** 登录用户  
**我想要** 登出  
**以便于** 清除会话

**API:** `POST /api/auth/logout`

### US-1.4 获取用户画像
**作为** 登录用户  
**我想要** 查看我的画像  
**以便于** 了解学习背景

**API:** `GET /api/user/profile`

### US-1.5 更新用户画像
**作为** 登录用户  
**我想要** 更新我的画像  
**以便于** 个性化学习

**API:** `PUT /api/user/profile`
```

- [ ] **Step 2: 创建 epic-1-auth/contract.md**

```markdown
# Epic 1 API 契约

## 认证接口

### POST /api/auth/register
**Request:**
```json
{"email": "string", "password": "string"}
```
**Response (200):**
```json
{"success": true, "data": {"user": {"id": "string"}, "token": "string"}}
```

### POST /api/auth/login
**Request:**
```json
{"email": "string", "password": "string"}
```
**Response (200):**
```json
{"success": true, "data": {"user": {"id": "string"}, "token": "string"}}
```

### POST /api/auth/logout
**Headers:** `Authorization: Bearer <token>`
**Response (200):**
```json
{"success": true, "data": {}}
```

## 用户画像接口

### GET /api/user/profile
**Headers:** `Authorization: Bearer <token>`
**Response (200):**
```json
{"success": true, "data": {
  "occupation": "string",
  "education": "string", 
  "programmingLevel": "入门|熟练",
  "mathLevel": "入门|熟练",
  "abilities": ["string"],
  "masteredKnowledge": ["string"]
}}
```

### PUT /api/user/profile
**Headers:** `Authorization: Bearer <token>`
**Request:** 同上 (partial update allowed)
**Response (200):** 同上
```

- [ ] **Step 3: 创建 epic-2-graph/be.md**

```markdown
# Epic 2: 图谱核心

## 用户故事

### US-2.1 创建学习计划
**作为** 学习者  
**我想要** 创建学习计划  
**以便于** 开始学习路径

**API:** `POST /api/plans`

### US-2.2 获取计划列表
**作为** 学习者  
**我想要** 查看我的计划列表  
**以便于** 选择学习内容

**API:** `GET /api/plans`

### US-2.3 获取图谱
**作为** 学习者  
**我想要** 查看图谱详情  
**以便于** 了解知识依赖

**API:** `GET /api/plans/{plan_id}/graph`

### US-2.4 更新节点状态
**作为** 学习者  
**我想要** 标记节点学习状态  
**以便于** 追踪进度

**API:** `PUT /api/plans/{plan_id}/nodes/{node_id}/status`

### US-2.5 保存节点位置
**作为** 学习者  
**我想要** 调整节点位置  
**以便于** 自定义图谱布局

**API:** `PUT /api/plans/{plan_id}/nodes/{node_id}/position`
```

- [ ] **Step 4: 创建 epic-2-graph/contract.md**

```markdown
# Epic 2 API 契约

## 计划接口

### POST /api/plans
**Request:**
```json
{
  "title": "string",
  "originalInput": "string",
  "targetNodeId": "string",
  "nodes": [{"id": "string", "name": "string", ...}],
  "edges": [{"from_node": "string", "to_node": "string"}]
}
```

### GET /api/plans
**Response:**
```json
{"success": true, "data": [{"id": "string", "title": "string", "progress": 0, "total": 0, "status": "active"}]}

### GET /api/plans/{plan_id}/graph
**Response:**
```json
{"success": true, "data": {
  "planId": "string",
  "title": "string", 
  "nodes": [...],
  "edges": [...]
}}
```

### PUT /api/plans/{plan_id}/nodes/{node_id}/status
**Request:** `{"status": "unlearned|learned|skipped"}`
```

- [ ] **Step 5: 创建 epic-3-notes, epic-4-ai, epic-5-stats** (结构同 epics 1-2)

**注意:** 每个 Epic 包含 be.md + fe.md + contract.md

- [ ] **Step 6: Commit**

```bash
git add docs/spec/epic-1-auth/ docs/spec/epic-2-graph/ docs/spec/epic-3-notes/ docs/spec/epic-4-ai/ docs/spec/epic-5-stats/
git commit -m "docs: add Epic spec files (be.md, contract.md)"
```

---

### Task 3: 清理旧文档

**Files:**
- Delete: `docs/spec/archive/` (全部 -done.md)
- Delete: `docs/spec/进度总览.md`
- Delete: `docs/spec/后端-通用规范.md` (被 Epic spec 取代)

- [ ] **Step 1: 确认 archive/ 内容**

```bash
ls docs/spec/archive/
```

预期输出: `后端-*.md`, `前端-*.md` 等 -done 文件

- [ ] **Step 2: 删除旧文档**

```bash
rm -rf docs/spec/archive/
rm docs/spec/进度总览.md
rm docs/spec/后端-通用规范.md
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: remove obsolete archive/ and progress doc"
```

---

## Chunk 2: 后端代码模块化

### Task 4: 创建 epic_N/ 目录结构

**Files:**
- Create: `backend/epic_1/__init__.py`
- Create: `backend/epic_1/models.py`
- Create: `backend/epic_1/utils.py`
- Create: `backend/epic_2/__init__.py`
- Create: `backend/epic_2/models.py`
- ... (epic_3, epic_4, epic_5 同理)

- [ ] **Step 1: 创建 epic_1/models.py** (从 models.py 拆分)

```python
"""Epic 1: 认证与用户 - Pydantic 模型"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user: dict
    token: str
    expiresIn: int = 604800


class UserProfile(BaseModel):
    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = "入门"
    mathLevel: Optional[str] = "入门"
    abilities: List[str] = []
    masteredKnowledge: List[str] = []


class UpdateProfileRequest(BaseModel):
    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = None
    mathLevel: Optional[str] = None
    abilities: Optional[List[str]] = None
```

- [ ] **Step 2: 创建 epic_1/utils.py**

```python
"""Epic 1: 认证工具函数"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

- [ ] **Step 3: 同样创建 epic_2, epic_3, epic_4, epic_5/models.py**

**Epic 2 (图谱):** NodeStatus, NodeData, Edge, GraphResponse, PlanCreateRequest 等
**Epic 3 (笔记):** Note 相关模型
**Epic 4 (AI):** ParseGoalRequest, GenerateGraphRequest, ClarifyGoalRequest 等
**Epic 5 (统计):** StatsOverview, StatsDistribution 等

- [ ] **Step 4: Commit**

```bash
git add backend/epic_1/ backend/epic_2/ backend/epic_3/ backend/epic_4/ backend/epic_5/
git commit -m "refactor: add epic_N/ directory structure"
```

---

### Task 5: 拆分 models.py

**Files:**
- Modify: `backend/models.py` (内容拆分到 epic_N/models.py)
- Update: 所有 import models 的文件

- [ ] **Step 1: 分析当前 models.py 结构**

读取 `backend/models.py`，识别每个模型属于哪个 Epic:

| 模型 | Epic |
|------|------|
| NodeStatus, NodeData, NodeBase, NodeCreate, NodeUpdate | epic-2 |
| Edge, GraphResponse | epic-2 |
| PlanSummary, PlanCreateRequest, PlanUpdateRequest | epic-2 |
| Note, NoteCreate, NoteUpdate | epic-3 |
| ParseGoalRequest/Response, GenerateGraphRequest/Response | epic-4 |
| RecommendNextRequest/Response | epic-4 |
| StatsOverview, StatsDistribution | epic-5 |
| RegisterRequest, LoginRequest, AuthResponse, UserProfile | epic-1 |

- [ ] **Step 2: 更新 backend/models.py 为 facade**

```python
"""Pydantic 模型 - 从 epic_N.models 重新导出"""

# 为了向后兼容，保持原有 import 结构
# 新代码应从 epic_N.models 导入

from typing import List, Optional, Dict, Any
from enum import Enum

# Re-export 所有模型以保持向后兼容
from epic_1.models import (
    RegisterRequest, LoginRequest, AuthResponse,
    UserProfile, UpdateProfileRequest,
)
from epic_2.models import (
    NodeStatus, NodeData, NodeBase, NodeCreate, NodeUpdate,
    Edge, GraphResponse, PlanSummary, PlanCreateRequest, PlanUpdateRequest,
    PlanListResponse, PlanUpdateResponse,
)
from epic_3.models import (
    Note, NoteCreate, NoteUpdate, NoteListResponse,
)
from epic_4.models import (
    ParseGoalRequest, ParseGoalResponse,
    GenerateGraphRequest, GenerateGraphResponse,
    ClarifyGoalRequest, ClarifyGoalResponse,
    RecommendNextRequest, RecommendNextResponse,
    AiRecommendRequest, AiRecommendResponse,
    AiClarifyRequest, AiClarifyResponse,
    ApplyChangesRequest, ApplyChangesResponse,
    BackgroundItem, BackgroundSummary, SplitSuggestion, Resource,
    GraphNode, GraphEdge, UserBackgroundInput, GraphChanges,
    ParseGoalAIResult, GenerateGraphAIResult, ClarifyGoalAIResult,
    RecommendNextAIResult, ApiError, ErrorResponse,
)
from epic_5.models import (
    StatsOverview, StatsDistribution,
)
```

- [ ] **Step 3: 更新 routers/auth.py import**

```python
# 从
from models import RegisterRequest, LoginRequest, AuthResponse, UserProfile

# 改为
from epic_1.models import RegisterRequest, LoginRequest, AuthResponse, UserProfile
# 或向后兼容
from models import RegisterRequest, LoginRequest, AuthResponse, UserProfile
```

- [ ] **Step 4: 同样更新 routers/plans.py, routers/graph.py 等**

- [ ] **Step 5: Commit**

```bash
git add backend/models.py
git add backend/routers/auth.py backend/routers/user.py
git add backend/routers/plans.py backend/routers/graph.py
git add backend/routers/notes.py backend/routers/stats.py backend/routers/ai.py
git commit -m "refactor: split models.py into epic_N/models.py"
```

---

## Chunk 3: 测试重组

### Task 6: 按 Epic 组织测试

**Files:**
- Create: `backend/tests/epic_1/`
- Create: `backend/tests/epic_2/`
- Create: `backend/tests/epic_3/`
- Create: `backend/tests/epic_4/`
- Create: `backend/tests/epic_5/`
- Move: 现有测试文件到对应 epic_N/

- [ ] **Step 1: 分析现有测试归属**

| 测试文件 | Epic |
|---------|------|
| test_auth*.py | epic-1 |
| test_user*.py | epic-1 |
| test_plans*.py | epic-2 |
| test_graph*.py | epic-2 |
| test_notes*.py | epic-3 |
| test_ai*.py | epic-4 |
| test_stats*.py | epic-5 |
| test_api_contract.py | 全局 |

- [ ] **Step 2: 移动测试文件**

```bash
mkdir -p backend/tests/epic_1 backend/tests/epic_2 backend/tests/epic_3 backend/tests/epic_4 backend/tests/epic_5

mv backend/tests/test_auth*.py backend/tests/epic_1/
mv backend/tests/test_user*.py backend/tests/epic_1/
mv backend/tests/test_plans*.py backend/tests/epic_2/
mv backend/tests/test_graph*.py backend/tests/epic_2/
mv backend/tests/test_notes*.py backend/tests/epic_3/
mv backend/tests/test_ai*.py backend/tests/epic_4/
mv backend/tests/test_stats*.py backend/tests/epic_5/
```

- [ ] **Step 3: 移动 conftest.py 到 tests/ 根目录 (如需要)**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: reorganize tests into tests/epic_N/"
```

---

## Chunk 4: README 和文档清理

### Task 7: 更新 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md 中的文档引用**

移除:
- `docs/spec/进度总览.md`
- `docs/architecture/` 引用 (如有)

添加:
- `docs/spec/AGENTS.md`
- `docs/spec/epic-N/` (Epic spec 索引)

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README to reference new spec structure"
```

---

## Chunk 5: 收尾

### Task 8: 最终检查

- [ ] **Step 1: 验证导入**

```bash
cd backend && python -c "from models import *; print('OK')"
```

预期: `OK`

- [ ] **Step 2: 运行测试**

```bash
cd backend && python -m pytest -q
```

预期: 所有测试通过

- [ ] **Step 3: 检查文档结构**

```bash
find docs/spec -name "*.md" | head -20
```

预期: AGENTS.md, DOD.md, CLAUDE.md, epic-1*/, epic-2*/ 等

- [ ] **Step 4: Commit 清理**

```bash
git add -A && git status
```

---

## 执行顺序

1. **Chunk 1**: 文档结构重组 (AGENTS.md, DOD.md, Epic specs)
2. **Chunk 2**: 后端代码模块化 (epic_N/ + 拆分 models.py)
3. **Chunk 3**: 测试重组 (tests/epic_N/)
4. **Chunk 4**: README 更新
5. **Chunk 5**: 收尾验证

**每个 Chunk 独立可测试，失败可回滚。**
