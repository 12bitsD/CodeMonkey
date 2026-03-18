# CLAUDE.md — AI Session 入口

> 每次 session 开始先读这个文件。这是 AI 写代码需要的全部边界信息。  
> 完整合同细节 → `后端-通用规范.md`（后端）/ `前端-架构总览.md`（前端）

---

## 1. 项目布局

```
CodeMonkey/
├── ConceptTree/
│   ├── backend/          FastAPI 应用
│   │   ├── main.py       FastAPI 入口，注册所有 router
│   │   ├── models.py     所有 Pydantic 模型（唯一真相）
│   │   ├── database.py   DB 连接（psycopg2，? → %s 占位符转换）
│   │   ├── config.py     Settings dataclass，从 .env 读取
│   │   ├── routers/      auth / user / plans / graph / notes / stats / ai
│   │   ├── services/     ai_service.py + llm/(client/providers/configs)
│   │   └── utils/        auth.py / password.py / id_generator.py
│   └── frontend/         React 18 + Vite 应用
│       └── src/
│           ├── pages/    AuthPage / HomePage / GraphPage / MyLearningPage
│           ├── components/ ui/ common/ node/
│           ├── contexts/ AppContext.jsx / AuthContext.jsx
│           ├── services/ api.js（唯一后端调用入口）
│           ├── hooks/    useGraphInteraction.js
│           └── utils/    progress.js
└── docs/
    ├── spec/             AI 必读合同（本目录）
    ├── architecture/     设计文档（按需注入）
    └── devlog/           Session 日志
```

---

## 2. Tech Stack

| 层 | 技术 | 版本 / 细节 |
|----|------|-------------|
| 后端语言 | Python | 3.9+ |
| 后端框架 | FastAPI | 0.128.x |
| 数据验证 | Pydantic v2 | models.py 是唯一真相 |
| 数据库 | Supabase PostgreSQL | psycopg2；schema.sql 是唯一真相 |
| 认证 | JWT (HS256) | `utils/auth.py`；7天有效 |
| LLM | Kimi 2.5 (kimi-k2-5) | `services/llm/`；OpenAI SDK兼容 |
| 前端框架 | React 18 + Vite 4 | |
| 路由 | React Router 6 | |
| 状态管理 | Context API | AppContext + AuthContext |
| 样式 | Tailwind CSS 3 | |
| 图标 | Lucide React | |
| 前端测试 | Vitest + Playwright | `npm run test:unit` / `test:e2e` |
| 后端测试 | pytest | `python -m pytest -q` |

---

## 3. 后端编码约束

### 3.1 API 响应格式（硬性规定，绝不能偏离）

```python
# 成功
{"success": True, "data": {...}}

# 失败 — 必须是这个结构，不能是 FastAPI 默认的 {"detail": ...}
{"success": False, "error": {"code": "ERROR_CODE", "message": "人类可读描述"}}
```

### 3.2 认证模式

```python
# 所有业务接口（除 /auth/register、/auth/login）必须依赖：
current_user_id: str = Depends(get_current_user_id)

# 数据隔离：必须用 current_user_id 过滤，不能用请求体里的 user_id
```

### 3.3 数据库占位符

```python
# 必须用 ? 占位符（database.py 会自动转成 %s）
db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,))
# 禁止直接用 %s 或 f-string 拼 SQL
```

### 3.4 禁止事项

- 禁止在路由函数里写业务逻辑（业务逻辑放 services/）
- 禁止用 `as any` 或类型抑制
- 禁止空的 `except` 块
- 禁止硬编码 user_id（必须从 token 中获取）
- 禁止返回非 `{success, data/error}` 结构的响应

### 3.5 错误码规范

| 场景 | 错误码 |
|------|--------|
| 计划不存在 | `PLAN_NOT_FOUND` |
| 节点不存在 | `NODE_NOT_FOUND` |
| 笔记不存在 | `NOTE_NOT_FOUND` |
| 无权限 | `FORBIDDEN` |
| AI调用失败 | `AI_SERVICE_ERROR` |
| 邮箱已注册 | `EMAIL_EXISTS` |
| 凭证错误 | `INVALID_CREDENTIALS` |

---

## 4. 前端编码约束

### 4.1 API 调用

```javascript
// 所有后端调用必须经过 services/api.js
// 禁止在组件里直接 fetch()

// edges 字段映射（后端用 from_node/to_node，前端用 from/to）
// api.js 已有 mapEdgesFromBackend / mapEdgesToBackend，必须用这两个函数
```

### 4.2 全局状态

```javascript
// 计划/笔记/画像 → AppContext（contexts/AppContext.jsx）
// token/登录态 → AuthContext（contexts/AuthContext.jsx）
// 局部 UI 状态 → useState，不要往 Context 里塞
```

### 4.3 Toast 通知

```javascript
// 所有错误/成功提示必须用 Toast，禁止 alert() 或 console.error() 给用户看
import { useToast } from '../contexts/ToastContext'
const toast = useToast()
toast.error('操作失败') / toast.success('已保存')
```

### 4.4 路由与保护

```
/            → HomePage（公开）
/auth        → AuthPage（公开，已登录自动跳转首页）
/graph/:planId → GraphPage（需 ProtectedRoute）
/my-learning → MyLearningPage（需 ProtectedRoute）
```

### 4.5 禁止事项

- 禁止绕过 `services/api.js` 直接调用后端
- 禁止在 AppContext 以外独立管理计划/笔记数据
- 禁止使用 LocalStorage 存业务数据（token 除外，存 `concept_tree_token`）

---

## 5. 关键 Patterns

### 5.1 新增后端接口

1. 在 `routers/` 下对应文件加路由函数
2. 在 `models.py` 加 Request/Response Pydantic 模型
3. 在 `main.py` 确认 router 已注册（若是新文件需手动 include）
4. 更新 `docs/spec/后端-通用规范.md` 接口清单

### 5.2 AI 服务接入

```
routers/ai.py → services/ai_service.py → services/llm/client.py
                                        → services/llm/configs/{action}.json (Prompt)
                                        → services/llm/providers/openai_compatible.py
```

Prompt 配置在 `services/llm/configs/*.json`，不需要改代码就能调 Prompt。

### 5.3 节点状态变更（完整链路）

```javascript
// 前端：GraphPage.handleNodeStatusChange
// → graphApi.updateNodeStatus(planId, nodeId, status)   [API call]
// → actions.updateNodeStatusInPlan(planId, nodeId, status) [AppContext, 同步首页进度]

// 后端：PUT /api/plans/{plan_id}/nodes/{node_id}/status
// → 更新 nodes.status
// → 更新 plans.progress / plans.total
// → 插入 learning_sessions 记录
// → 若 status='learned'：更新 user_profiles.mastered_knowledge
```

### 5.4 用户画像（user_background）传递链路

```
前端 AppContext.userProfile
→ api.js generateGraph(input, interpretation, userBackground)
→ POST /api/ai/generate-graph { userBackground: {...} }
→ ai.py → ai_service.generate_graph(user_background=user_bg)
→ generate_graph.json prompt 中注入 {{background}}
```

---

## 6. 数据库表速查

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `users` | 用户账号 | `id(u_前缀)`, `email`, `password_hash` |
| `user_profiles` | 用户画像 | `user_id`, `occupation`, `programming_level`, `math_level`, `abilities(JSONB)`, `mastered_knowledge(JSONB)` |
| `plans` | 学习计划 | `id(p_前缀)`, `user_id`, `title`, `status(active/archived)`, `progress`, `total` |
| `nodes` | 知识节点 | `id`, `plan_id`, `name`, `status(unlearned/learned/skipped)`, `x`, `y`, `why`, `what(JSONB)`, `mastery(JSONB)`, `prompt`, `resources(JSONB)`, `is_target`, `domain` |
| `edges` | 节点依赖边 | `id(e_前缀)`, `plan_id`, `from_node_id`, `to_node_id` |
| `notes` | 学习笔记 | `id(note_前缀)`, `plan_id`, `node_id`, `user_id`, `content` |
| `learning_sessions` | 学习记录 | `id(UUID)`, `user_id`, `plan_id`, `node_id`, `action` |

---

## 7. 环境变量（`ConceptTree/backend/.env`）

```env
DATABASE_URL=postgresql://...    # Supabase 连接串
JWT_SECRET_KEY=...               # JWT 签名密钥
LLM_API_KEY=sk-...               # Kimi API Key（必填）
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=kimi-k2-5
LLM_FALLBACK_API_KEY=...         # 备用 LLM（可选）
```

---

## 8. 当前 MVP 状态

**所有核心功能已完成（Phase 1–11 全部 ✅）**

待优化（不影响功能）：
- logout 未实现 token 黑名单
- notes 搜索为 LIKE（未用 FTS）
- LLM 未实现响应缓存

详细状态 → `进度总览.md`
