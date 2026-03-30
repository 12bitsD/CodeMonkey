# CLAUDE.md — AI Session 入口

> 每次 session 开始先读这个文件。
> 完整合同细节 → `docs/spec/epic-N/` (Epic spec) / `docs/design/` (架构约束)

---

## 必读文档

| 文档 | 说明 |
|------|------|
| `docs/spec/AGENTS.md` | **Agent 操作手册** — 先读这个 |
| `docs/spec/DOD.md` | 完成标准 — 提交前检查 |
| `docs/spec/epic-N/be.md` | 当前 Epic 后端需求 |
| `docs/spec/epic-N/contract.md` | API 契约 |
| `docs/design/BACKEND.md` | 后端架构约束 |
| `docs/design/FRONTEND.md` | 前端架构约束 |

---

## 快速开始

1. 读 `docs/spec/AGENTS.md`
2. 读对应 Epic 的 be.md + contract.md
3. 照 TDD 流程实现
4. 逐项检查 DoD

---

## 项目布局

```
CodeMonkey/
├── ConceptTree/
│   ├── backend/          FastAPI 应用
│   │   ├── main.py       FastAPI 入口
│   │   ├── models.py     Pydantic 模型
│   │   ├── database.py   DB 连接
│   │   ├── config.py     配置
│   │   ├── routers/      API 路由
│   │   ├── services/     业务逻辑 (AI服务等)
│   │   └── tests/        测试 (按 epic_N 组织)
│   │
│   └── frontend/         React 18 + Vite 应用
│       └── src/
│           ├── pages/    页面组件
│           ├── components/ ui/ common/ node/
│           ├── contexts/ AppContext / AuthContext
│           ├── services/ api.js (唯一后端调用入口)
│           └── hooks/    useGraphInteraction
│
└── docs/
    ├── spec/             Epic 规格文档
    │   ├── AGENTS.md     Agent 操作手册
    │   ├── DOD.md       完成标准
    │   ├── epic-1-auth/ 认证与用户
    │   ├── epic-2-graph/ 图谱核心
    │   ├── epic-3-notes/ 笔记
    │   ├── epic-4-ai/  AI 服务
    │   └── epic-5-stats/ 统计
    └── design/           架构约束
        ├── BACKEND.md
        └── FRONTEND.md
```

---

## Tech Stack

| 层 | 技术 |
|----|------|
| 后端 | Python 3.9+, FastAPI, Pydantic v2 |
| 数据库 | PostgreSQL (Supabase), psycopg2 |
| 认证 | JWT (HS256), 7天有效 |
| AI | Kimi 2.5 (moonshot-v1-8k) |
| 前端 | React 18, Vite 4, Tailwind CSS 3 |
| 状态 | Context API |
| 测试 | pytest (后端), Vitest + Playwright (前端) |

---

## 开发规则

1. **读规范先于写代码** — 读 `docs/spec/AGENTS.md`
2. **TDD 流程** — 先写测试，再实现
3. **测试不通过不提交**
4. **DoD 逐项检查** — 读 `docs/spec/DOD.md`
5. **规范与代码同步** — 改 API 必改 contract.md

---

## API 响应格式

```python
# 成功
{"success": True, "data": {...}}

# 失败
{"success": False, "error": {"code": "ERROR_CODE", "message": "..."}}
```

---

## 禁止事项

- 禁止绕过 `services/api.js` 直接调用后端
- 禁止在 AppContext 外独立管理计划/笔记数据
- 禁止硬编码 user_id (必须从 token 获取)
- 禁止返回非 `{success, data/error}` 结构的响应
- 禁止空的 `except` 块

---

## 错误码规范

| 前缀 | 模块 |
|------|------|
| `PLAN_*` | 计划 |
| `NODE_*` | 节点 |
| `NOTE_*` | 笔记 |
| `AI_*` | AI 服务 |
| `AUTH_*` | 认证 |
