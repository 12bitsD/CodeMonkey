# ConceptTree 采用 bitsNovels 架构模式重构设计

**日期**: 2026-03-30  
**状态**: Draft  
**目标**: 采用 bitsNovels 的文档体系和代码组织模式，提升 AI Agent 协作开发效率

---

## 1. 背景与目标

### 当前问题

| 问题 | 影响 |
|------|------|
| `docs/spec/CLAUDE.md` 声明但不存在 | AI Agent 无法找到规范入口 |
| `docs/spec/后端-通用规范.md` 不存在 | API 契约无文档 |
| 后端 routers 虽模块化但无 Epic 组织 | 新功能归属不清晰 |
| 无 AGENTS.md / DoD | AI Agent 工作流不标准 |
| 前端 GraphPage 无单元测试 | 重构风险高 |

### 目标

1. **文档体系完整** — AI Agent 可直接照着文档执行
2. **代码组织清晰** — 按 Epic/功能模块拆分，便于定位
3. **工程实践标准化** — TDD 流程、DoD 检查、契约验证

---

## 2. 架构设计

### 2.1 文档结构

```
ConceptTree/
├── docs/
│   ├── superpowers/
│   │   └── specs/                              # 设计文档
│   │       └── 2026-03-30-refactor-design.md
│   │
│   ├── specs/                                  # Spec 文档 (重构后)
│   │   ├── CLAUDE.md                          # AI 入口 (重建)
│   │   ├── AGENTS.md                          # Agent 操作手册 (新增)
│   │   ├── DOD.md                             # 完成标准 (新增)
│   │   │
│   │   ├── epic-1-auth/                       # Epic 1: 认证与用户
│   │   │   ├── be.md                          # 后端需求
│   │   │   ├── fe.md                          # 前端需求
│   │   │   └── contract.md                    # API 契约
│   │   │
│   │   ├── epic-2-graph/                       # Epic 2: 图谱核心
│   │   │   ├── be.md
│   │   │   ├── fe.md
│   │   │   └── contract.md
│   │   │
│   │   ├── epic-3-notes/                       # Epic 3: 笔记
│   │   │   ├── be.md
│   │   │   ├── fe.md
│   │   │   └── contract.md
│   │   │
│   │   ├── epic-4-ai/                         # Epic 4: AI 服务
│   │   │   ├── be.md
│   │   │   ├── fe.md
│   │   │   └── contract.md
│   │   │
│   │   └── epic-5-stats/                       # Epic 5: 统计
│   │       ├── be.md
│   │       ├── fe.md
│   │       └── contract.md
│   │
│   └── design/                                # 架构设计文档
│       ├── BACKEND.md                         # 后端架构规范
│       └── FRONTEND.md                        # 前端架构规范
```

### 2.2 代码结构 (按 Epic 组织)

```
ConceptTree/
├── backend/
│   ├── main.py                                # 入口 (保持)
│   ├── models.py                              # Pydantic 模型 (保持)
│   ├── database.py                            # DB 连接 (保持)
│   │
│   ├── routers/                               # 路由 (重组)
│   │   ├── __init__.py
│   │   ├── auth.py                            # Epic 1: /api/auth/*
│   │   ├── user.py                            # Epic 1: /api/user/*
│   │   ├── plans.py                           # Epic 2: /api/plans/*
│   │   ├── graph.py                           # Epic 2: /api/plans/{id}/graph
│   │   ├── notes.py                           # Epic 3: /api/notes/*
│   │   ├── stats.py                           # Epic 5: /api/stats/*
│   │   └── ai.py                              # Epic 4: /api/ai/*
│   │
│   ├── services/                              # 业务逻辑 (重组)
│   │   ├── ai_service.py                      # Epic 4: AI 服务
│   │   ├── learning_history.py                 # Epic 4: 学习历史
│   │   └── llm/                               # Epic 4: LLM 集成
│   │       ├── client.py
│   │       ├── providers/
│   │       └── configs/
│   │
│   ├── epic_1/                                # Epic 1 模块 (新增)
│   │   ├── __init__.py
│   │   ├── models.py                          # 认证相关 Pydantic 模型
│   │   └── utils.py                           # 认证工具函数
│   │
│   ├── epic_2/                                # Epic 2 模块 (新增)
│   │   ├── __init__.py
│   │   └── models.py                          # 图谱相关模型
│   │
│   ├── epic_3/                                # Epic 3 模块 (新增)
│   │   ├── __init__.py
│   │   └── models.py                          # 笔记相关模型
│   │
│   ├── epic_4/                                # Epic 4 模块 (新增)
│   │   ├── __init__.py
│   │   └── models.py                          # AI 相关模型
│   │
│   ├── epic_5/                                # Epic 5 模块 (新增)
│   │   ├── __init__.py
│   │   └── models.py                          # 统计相关模型
│   │
│   └── tests/                                 # 测试 (重组)
│       ├── epic_1/                            # Epic 1 测试
│       ├── epic_2/                            # Epic 2 测试
│       ├── epic_3/                            # Epic 3 测试
│       ├── epic_4/                            # Epic 4 测试
│       ├── epic_5/                            # Epic 5 测试
│       └── test_api_contract.py               # 全局 API 契约测试
```

---

## 3. 关键文档内容

### 3.1 AGENTS.md (Agent 操作手册)

```markdown
# Agent 操作手册

## 快速开始

1. 读 `docs/spec/AGENTS.md` (本文件)
2. 读对应的 Epic spec (见下方)
3. 照 TDD 流程实现
4. 逐项检查 DoD

## 4 文件任务包

每个 Epic 功能需要读取:

1. `docs/spec/epic-N/be.md` — 后端需求 (BE)
2. `docs/spec/epic-N/fe.md` — 前端需求 (FE)
3. `docs/spec/contract.md` — API 契约
4. `docs/design/BACKEND.md` — 架构约束

## TDD 铁律

任何功能必须:
1. 先写红灯测试
2. 实现通过测试
3. 重构

## 完成标准 (DoD)

见 `docs/spec/DOD.md`
```

### 3.2 DoD.md (完成标准)

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
- [ ] 类型定义已同步 (models.py)
```

### 3.3 Epic Spec 示例 (epic-2/be.md)

```markdown
# Epic 2: 图谱核心

## 用户故事

### US-2.1 获取图谱
**作为** 学习者  
**我想要** 查看学习计划的图谱  
**以便于** 了解知识节点之间的关系

### 验收标准 (AC)
- 返回 plan 所有节点和边
- 节点包含: id, name, status, x, y, why, what, mastery, resources
- 边包含: from_node, to_node
- 仅返回属于该 plan 的数据

### API 端点
- `GET /api/plans/{plan_id}/graph`

### 业务逻辑
1. 验证 plan_id 存在且属于当前用户
2. 查询 nodes 表 (plan_id = ?)
3. 查询 edges 表 (plan_id = ?)
4. 组装 GraphResponse
```

---

## 4. 迁移策略

### 阶段 1: 文档先行

1. 创建 `docs/spec/CLAUDE.md` (AI 入口)
2. 创建 `docs/spec/AGENTS.md` (Agent 手册)
3. 创建 `docs/spec/DOD.md` (完成标准)
4. 创建 5 个 Epic spec 文件

### 阶段 2: 代码重组

1. 创建 `epic_N/` 目录结构
2. 将 Pydantic 模型从 `models.py` 拆分到对应 epic
3. 移动测试文件到 `tests/epic_N/`
4. 更新 `main.py` import 路径

### 阶段 3: 补充测试

1. 为 GraphPage 添加单元测试
2. 补充边界 case 测试
3. 添加 API 契约测试覆盖

---

## 5. 与 bitsNovels 的差异

| 方面 | bitsNovels | ConceptTree (本设计) |
|------|------------|---------------------|
| Epic 划分 | 按功能模块 (auth, projects, editor, AI, storage) | 按现有功能 (auth, graph, notes, AI, stats) |
| 代码模块化 | 计划中未落地 | 实际拆分 epic_N/ |
| 数据库 | 尚未集成 | 已集成 (需保持) |
| AI 集成 | 未实现 | 已实现 (Kimi 2.5) |

---

## 6. 成功标准

1. **AI Agent 可直接上手** — 读 AGENTS.md → 读 Epic spec → 实现
2. **代码归属清晰** — 每个文件属于某个 Epic
3. **测试覆盖完整** — 每个功能有对应测试
4. **文档与代码同步** — 改代码必改文档

---

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 迁移过程破坏现有功能 | 分阶段 + 测试验证 |
| 文档维护负担增加 | 最小化必改文档场景 |
| Agent 习惯旧模式 | AGENTS.md 提供明确指引 |
