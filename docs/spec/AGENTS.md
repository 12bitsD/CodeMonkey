# Agent 操作手册

> 本项目采用 bitsNovels 架构模式开发

## 快速开始

1. 读 `docs/spec/AGENTS.md` (本文件)
2. 读对应的 Epic spec (`docs/spec/epic-N/`)
3. 照 TDD 流程实现
4. 逐项检查 DoD

## 4 文件任务包

每个 Epic 功能需要读取以下 4 个文件：

| 文件 | 说明 |
|------|------|
| `docs/spec/epic-N/be.md` | 后端需求 (Business Engineering) |
| `docs/spec/epic-N/fe.md` | 前端需求 (FrontEnd) |
| `docs/spec/epic-N/contract.md` | API 契约 (接口定义) |
| `docs/design/BACKEND.md` | 架构约束 |

## TDD 铁律

任何功能必须遵循:

1. **红灯** — 先写测试，确保测试失败
2. **绿灯** — 实现最小代码，让测试通过
3. **重构** — 优化代码，保持测试通过

## Epic 索引

| Epic | 功能 | 后端路由 | 状态 |
|------|------|----------|------|
| epic-1 | 认证与用户 | `/api/auth/*`, `/api/user/*` | ✅ 已有 |
| epic-2 | 图谱核心 | `/api/plans/*`, `/api/plans/{id}/graph` | ✅ 已有 |
| epic-3 | 笔记 | `/api/notes/*` | ✅ 已有 |
| epic-4 | AI 服务 | `/api/ai/*` | ✅ 已有 |
| epic-5 | 统计 | `/api/stats/*` | ✅ 已有 |

## 开发流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 领任务 → 读 Epic 4 文件任务包                          │
│     ├── be.md (做什么)                                     │
│     ├── fe.md (前端做什么)                                 │
│     ├── contract.md (接口契约)                             │
│     └── design/BACKEND.md (架构约束)                       │
│                                                             │
│  2. 写测试 → TDD 红灯                                    │
│     ├── 在 tests/epic_N/ 下添加测试                       │
│     └── 运行 pytest 确保失败                               │
│                                                             │
│  3. 实现 → 照 spec 写代码                                 │
│                                                             │
│  4. 验证 → DoD 逐项检查                                   │
│     └── 读 docs/spec/DOD.md                               │
│                                                             │
│  5. 提交 → 契约检查                                       │
│     └── 确保 API 契约未被破坏                              │
└─────────────────────────────────────────────────────────────┘
```

## 禁止事项

- 禁止绕过 `services/api.js` 直接调用后端
- 禁止在 AppContext 以外独立管理计划/笔记数据
- 禁止使用 LocalStorage 存业务数据 (token 除外)
- 禁止硬编码 user_id (必须从 token 获取)
- 禁止返回非 `{success, data/error}` 结构的响应

## 文档位置

```
docs/spec/
├── AGENTS.md           ← Agent 操作手册 (本文件)
├── DOD.md              ← 完成标准
├── CLAUDE.md           ← AI Session 入口 (必读)
├── epic-1-auth/       ← Epic 1: 认证与用户
├── epic-2-graph/       ← Epic 2: 图谱核心
├── epic-3-notes/       ← Epic 3: 笔记
├── epic-4-ai/         ← Epic 4: AI 服务
└── epic-5-stats/       ← Epic 5: 统计

docs/design/
├── BACKEND.md          ← 后端架构约束
└── FRONTEND.md         ← 前端架构约束
```
