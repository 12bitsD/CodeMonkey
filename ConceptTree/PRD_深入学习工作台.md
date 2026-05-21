# PRD：深入学习工作台（Deep Learning Workspace）

> 版本：v0.3  
> 日期：2026-05-19  
> 状态：审核修订 — 消除 schema 冲突、状态歧义，对齐 PostgreSQL/Supabase

---

## 修订记录（v0.3）

针对 v0.2 在 coding 阶段出现的歧义和冲突，做如下修订：

1. **合并 PROBING 状态**：第一个概念的讲解同时承担难度探测职责，删除独立 PROBING 状态
2. **统一 Assessment Agent 输出**：单题评估和综合判定使用两个明确独立的 schema
3. **简化 Teaching Agent 输出**：删除未使用字段 `dalle_prompt`、`is_concept_done`
4. **明确测试题数量**：综合测试固定 3 题，单题评估后循环出题，全部答完做综合判定
5. **concepts_status 改用 index 做 key**：避免长中文字符串作 JSON key 的转义风险
6. **数据库 schema 改 PostgreSQL 语法**：UUID/TIMESTAMPTZ/JSONB，直接在 Supabase SQL Editor 执行
7. **API endpoints 收敛**：删除 `/submit-test`、`/restart`、`/generate-note`，全部通过 `/message` 和 `/command` 触发
8. **节点元数据流向明确**：`POST /sessions` 返回时附带 `node_name`、`node_why`、`what_list`

---

## 一、Feature Overview

### 背景与动机

当前节点学习体验停留在"看解释"层面：每个 what 项只有一段 AI 解释，缺乏结构化的学习路径和扎实的掌握验证。用户无法确认自己是否真正学会了一个节点。

### 核心目标

把每个节点从"一段解释"升级为**完整的 1v1 AI 家教工作台**：

- AI 按认知科学原则逐概念教学，动态校准难度
- 学习完成后通过综合测试，AI 判定是否掌握
- 通过后生成个性化学习笔记，作为复习凭证
- 记忆系统持续积累用户画像，实现真正的个性化教学

### 入口

节点详情页 → "深入学习"按钮 → 跳转至 `/deep-learn/:planId/:nodeId`

---

## 二、核心用户旅程

```
进入工作台
    │
    ▼
Session Orchestrator 检查：是否有 in_progress session？
    ├── 有 → 断点续学（从 deep_learn_sessions 恢复 state）
    └── 无 → 新建 session
    │
    ▼
[讲解第一个概念] Teaching Agent 输出讲解 + 题目
    （首次回答用于校准初始难度，无需独立探测回合）
    │
    ▼
循环（每个 what 项）：
  [讲解概念 N] → [出题] → 用户答 → [评估] → [等待指令]
                                              │
                                  继续 / 展开 / 跳过 / 重讲
    │
    ▼
所有概念讲完或跳过
    │
    ▼
[Assessment Agent · 综合判定 schema] 判断是否准备好测试
    ├── ready=false → 推荐针对弱点再讲
    └── ready=true → 询问"准备好综合测试了吗？"
    │
    ▼
用户确认 → [综合测试·共 3 题]
  单题循环：出题 → 用户答 → 单题评估 → 出下一题
    │
    ▼ 全部 3 题答完
[Assessment Agent · 综合判定 schema] 判定通过/未通过
    ├── 通过 → 节点标记为 learned（Phase 3 再加完成笔记生成）
    └── 未通过 → 展示弱点 → 重新开始 / 针对弱点复习
```

---

## 三、状态机设计

### 状态定义

| 状态 | 描述 |
|------|------|
| `INITIALIZING` | session 刚创建，准备调 Teaching Agent 讲第一个概念 |
| `TEACHING` | Teaching Agent 正在生成讲解内容（流式输出中） |
| `QUESTIONING` | 当前概念讲完，AI 出题完毕，等待用户回答 |
| `EVALUATING` | Assessment Agent 评估用户单题回答 |
| `AWAITING_COMMAND` | 评估完毕，等待用户控制命令（继续/展开/跳过/重讲） |
| `AI_ASSESSING_READINESS` | 所有概念讲完，AI 用综合判定 schema 判断是否准备好测试 |
| `CONFIRMING_TEST` | AI 询问"准备好测试了吗"，等待用户确认 |
| `TESTING` | 综合测试阶段，正在出题或等待用户回答测试题 |
| `EVALUATING_TEST` | Assessment Agent 评估单道测试题；非最后一题转回 TESTING，最后一题转综合判定 |
| `CHOOSING_AFTER_FAIL` | 综合测试未通过，展示弱点，等待用户选择下一步 |
| `COMPLETED` | 综合测试通过，节点已标记为 learned |

> 备注：`GENERATING_NOTE` 状态在 Phase 3 引入。Phase 1 通过测试后直接进入 `COMPLETED`。

### 状态转换规则

```
INITIALIZING → TEACHING                  : session 创建后立即调 Teaching Agent 讲第一个概念
TEACHING → QUESTIONING                   : 讲解内容输出完毕，题目已生成
QUESTIONING → EVALUATING                 : 用户提交回答（普通学习阶段）
EVALUATING → AWAITING_COMMAND            : 单题评估完成，weak_points 更新
EVALUATING → QUESTIONING                 : 连续 2 次答错，Teaching Agent 切到 probe_stuck 模式追问
AWAITING_COMMAND → TEACHING              : 收到 continue（下一概念）/ expand（深入）/ skip（跳过）/ reteach（重讲）
AWAITING_COMMAND → AI_ASSESSING_READINESS: 所有概念已 done 或 skipped 时，收到 continue 触发
AI_ASSESSING_READINESS → CONFIRMING_TEST : 综合判定 schema 输出 ready_for_test=true
AI_ASSESSING_READINESS → TEACHING        : 综合判定 schema 输出 ready_for_test=false（补讲弱点）
CONFIRMING_TEST → TESTING                : 用户确认 confirm_test
CONFIRMING_TEST → TEACHING               : 用户选择 not_ready
TESTING → EVALUATING_TEST                : 用户提交本道测试题答案
EVALUATING_TEST → TESTING                : 还有未答测试题（共 3 题），出下一题
EVALUATING_TEST → COMPLETED              : 3 题全部答完且综合判定 passed=true，节点标 learned
EVALUATING_TEST → CHOOSING_AFTER_FAIL    : 3 题全部答完但综合判定 passed=false
CHOOSING_AFTER_FAIL → INITIALIZING       : 用户选择 restart（同时旧 session 标记为 abandoned）
CHOOSING_AFTER_FAIL → TEACHING           : 用户选择 not_ready（针对弱点复习）
任意状态 → INITIALIZING                  : 用户手动点击"重新开始"（旧 session 标 abandoned，开新 session）
```

### 关键设计原则

- **Orchestrator 用代码实现**（不是 LLM）：状态转换由后端代码控制，避免模型推断不准
- **每个状态决定 LLM 的 system prompt**：Teaching / Assessment / Note Generator 共享对话历史，但 system prompt 按状态精确切换
- **同一概念连续两次答错**：状态机记录 `wrong_count` 字段，触发后 Teaching Agent 收到指令"停止给答案，先询问用户卡在哪里"

---

## 四、Multi-Agent 架构

```
用户消息
    │
    ▼
Session Orchestrator（代码状态机）
    │
    ├─ 加载 Memory Context Block
    │       └── Memory Manager（LLM + DB）
    │
    ├─ 状态 == TEACHING / TESTING（出题阶段）
    │       └── Teaching Agent（LLM，主教学流程；Phase 1 内置 mermaid 决策，Phase 2 引入独立 Image Agent）
    │
    ├─ 状态 == EVALUATING / EVALUATING_TEST
    │       └── Assessment Agent · 单题评估 schema（评估 + 校准难度 + 更新弱点）
    │
    ├─ 状态 == AI_ASSESSING_READINESS / 全部测试题答完后
    │       └── Assessment Agent · 综合判定 schema（passed + 强弱区分析）
    │
    ├─ 状态 == GENERATING_NOTE
    │       └── Note Generator Agent（LLM，生成完成笔记）
    │
    └─ Session 结束时（异步）
            └── Memory Update Agent（提炼 session 经验 → 更新长期记忆）
```

### 各 Agent 职责详述

#### Teaching Agent

- **System Prompt 核心框架**（来自用户确认的教学原则）：
  - 每次只讲一个概念，工作记忆保护
  - 先"为什么需要它"，再 formal 定义（认知锚定）
  - 逻辑连续性：每句回答前一句引发的问号
  - 不主动延伸未讲过的概念
- **Memory Context 注入**：Phase 1 注入 short-term（recent_turns + weak_points）；Phase 2 扩展到四类
- **唯一的输出 schema**（任何状态都按这个返回）：
  ```json
  {
    "content": "讲解文本（Markdown 格式中文）",
    "questions": ["题目1（概念理解）", "题目2（应用/计算）", "题目3（误区陷阱）"],
    "needs_image": false,
    "image_type": null,
    "mermaid_code": null
  }
  ```
  - `questions` 在普通讲解后必填 2-3 条；在 `probe_stuck` 模式下可为空（只追问，不出题）
  - `image_type` Phase 1 仅 `"mermaid"` 或 `null`；Phase 2 引入 `"dalle"`

#### Assessment Agent（两套独立 schema）

**A. 单题评估 schema**（用于 EVALUATING、EVALUATING_TEST 中的逐题判定）

- **输入**：当前概念、对应题目、用户回答、本次 session 的 weak_points 与 wrong_count
- **输出**：
  ```json
  {
    "is_correct": true,
    "quality_score": 0.7,
    "explanation": "给用户看的一句话评价（鼓励性）",
    "feedback": "具体指出哪里对哪里有偏差",
    "update_weak_points": ["Prefill 计算复杂度"],
    "difficulty_delta": -1,
    "wrong_count": 1
  }
  ```

**B. 综合判定 schema**（用于 AI_ASSESSING_READINESS 和 3 题答完后的最终判定）

- **输入**：已覆盖/跳过的概念列表、累计 weak_points、（测试场景）3 道题的回答与单题评估结果
- **输出**：
  ```json
  {
    "passed": true,
    "confidence": 0.85,
    "ready_for_test": true,
    "reason": "一句话判定理由",
    "strong_areas": ["KV Cache 原理"],
    "weak_areas": ["Prefill 复杂度"],
    "suggest_review_concepts": []
  }
  ```
  - readiness 场景：使用 `ready_for_test` 和 `suggest_review_concepts`
  - 测试通过判定场景：使用 `passed`、`confidence`、`strong_areas`、`weak_areas`
  - `confidence < 0.6` 时，readiness 场景倾向 `ready_for_test=false`；测试场景由 prompt 约束不强行判定

#### Image Trigger Agent（轻量级）

分层策略，优先免费方案：

| 图类型 | 工具 | 触发条件 |
|--------|------|---------|
| 流程图 / 依赖图 | Mermaid.js | 有步骤顺序或依赖关系 |
| 数学公式 | KaTeX 渲染 | 包含数学推导 |
| 架构图 / 概念关系 | GPT Image 2 | 空间关系复杂，Mermaid 表达不足 |
| 真实世界类比图 | GPT Image 2 | 需要视觉直觉建立时 |

#### Memory Update Agent（异步，Session 结束后）

从整个对话历史提炼：
- 哪些概念顺利通过 → 更新 long-term 已掌握列表
- 哪些类比有效 → 更新 procedural memory
- 整体 session 摘要 → 写入 episodic memory

---

## 五、Memory 系统设计

### 四种记忆类型

| 类型 | 内容 | 存储位置 | 更新时机 |
|------|------|---------|---------|
| **Short-term（工作记忆）** | 最近 6-8 轮对话、本次难度校准值、当前弱点 | DB `deep_learn_sessions.recent_turns` | 每 3 轮 checkpoint；重要事件立刻写 |
| **Long-term（长期记忆）** | 整体能力画像、偏好学习风格、跨节点已掌握概念清单 | DB `user_learning_profile` | 重要事件触发（概念通过 / 弱点发现 / 测试结束） |
| **Episodic（情节记忆）** | 每次 session 摘要、历史测试结果、"上次在哪里卡住" | DB `learning_session_records` | 测试完成时（通过或未通过）写入摘要 |
| **Procedural（程序记忆）** | 对该用户有效的教学模式（代码类比 vs 数学推导） | DB `teaching_patterns` | 累积 3-5 次 session 后，Memory Update Agent 统计归纳 |

### Memory Context Block（注入给每次 LLM 调用）

```
[Memory Context]
长期记忆：用户有 Python 基础，数学偏弱，偏好从代码例子入手理解概念。
情节记忆：上次学习此节点（2026-05-10）在"Attention 机制"部分卡住，最终未通过测试。
程序记忆：代码类比比纯数学推导对该用户更有效；每个概念出 2 题效果最好。
当前状态：本次已讲完 KV Cache 基础（顺利），当前在讲 Prefill，用户答错 1 次。
```

---

## 六、UI/UX 规格

### 页面路由

`/deep-learn/:planId/:nodeId`

### 整体布局

```
┌──────────────────────────────────────────────────────────────────┐
│  ← 返回    [节点名] KV Cache    [重新开始]    [完成笔记 ↗]        │  ← Header
└──────────────────────────────────────────────────────────────────┘
┌─────────────────────────────┬────────────────────────────────────┐
│         左侧：学习导航        │           右侧：对话区              │
│                             │                                    │
│  进度  ████░░░░  2 / 5      │  ┌──────────────────────────────┐ │
│                             │  │  Teaching Agent 的讲解内容    │ │
│  概念列表：                  │  │  （Markdown 渲染）            │ │
│  ✓ KV Cache 基础            │  │                              │ │
│  → Prefill 阶段  ← 当前     │  │  [Mermaid 图嵌入对话流]       │ │
│  ○ Decode 阶段              │  │                              │ │
│  ○ Prompt Caching           │  │  题目：...                   │ │
│  ○ 工程实践                 │  └──────────────────────────────┘ │
│                             │                                    │
│  ─────────────────          │  [左侧对照图] 用户点击可展开        │
│  弱点追踪：                  │  （图嵌入对话流，同时可钉在左侧）    │
│  ⚠ Prefill 计算复杂度        │                                    │
│                             │  ┌──────────────────────────────┐ │
│  ─────────────────          │  │ 输入框...                    │ │
│  [📝 笔记] ← 弹窗入口        │  └──────────────────────────────┘ │
│                             │  [继续] [展开] [跳过] [重讲]       │
└─────────────────────────────┴────────────────────────────────────┘
```

### 关键 UI 组件

#### 图片展示策略（双轨）

- **主轨（嵌入对话流）**：图随讲解内容出现，自然推进，像知乎文章
- **辅轨（左侧钉图）**：用户可点击图片旁的"钉图"按钮，将图固定在左侧以对照文字学习
- 左侧钉图区支持多张，可关闭

#### 笔记弹窗

- 左下角"📝 笔记"入口
- 弹窗内：Markdown 实时渲染，支持用户手动编辑
- 自动记录：AI 讲解的关键定义会在讲完后提示"加入笔记？"
- 笔记与节点绑定，存入现有 notes 系统

#### 控制命令

- 按钮形式（可点击）+ 文字输入（可直接打"继续"）
- 状态说明：`AWAITING_COMMAND` 时按钮高亮，其他状态时灰色不可点

#### 完成笔记（测试通过后）

- Header 区出现"完成笔记 ↗"，点击跳转至笔记详情页
- 笔记风格：个人学习总结（不是教科书），包含本次学习轨迹、弱点与突破
- 格式：Markdown → 渲染成知乎文章风格

---

## 七、数据库 schema 与 API

> 数据库托管在 Supabase（PostgreSQL）。**所有 DDL 直接在 Supabase SQL Editor 执行**，不走 migration 工具链。后端代码假定下面的表和列已经存在，不要在 Python 里做 `CREATE TABLE` 或自动迁移逻辑。

### Phase 1 必需的表（SQL 直接在 Supabase 执行）

```sql
-- 1. Session 状态持久化（Phase 1 唯一新增表）
CREATE TABLE IF NOT EXISTS deep_learn_sessions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL,
  node_id               TEXT NOT NULL,
  plan_id               TEXT NOT NULL,
  state                 TEXT NOT NULL DEFAULT 'INITIALIZING',
  current_concept_index INTEGER NOT NULL DEFAULT 0,
  difficulty_level      INTEGER NOT NULL DEFAULT 3,        -- 1-5
  wrong_count_current   INTEGER NOT NULL DEFAULT 0,        -- 当前概念的连续错误次数
  concepts_status       JSONB NOT NULL DEFAULT '{}',       -- {"0":"done","1":"current","2":"skipped",...} 以 what_list index 为 key
  weak_points           JSONB NOT NULL DEFAULT '[]',       -- ["概念名"]
  recent_turns          JSONB NOT NULL DEFAULT '[]',       -- [{"role":"user","content":"..."}]
  what_list             JSONB NOT NULL DEFAULT '[]',       -- 创建 session 时快照节点的 what 列表
  conversation_summary  TEXT,                              -- Phase 2 长会话压缩用，Phase 1 暂不写
  test_questions        JSONB NOT NULL DEFAULT '[]',       -- 综合测试的 3 道题快照
  test_current_index    INTEGER NOT NULL DEFAULT 0,        -- 当前测试题序号 (0/1/2)
  test_results          JSONB NOT NULL DEFAULT '[]',       -- 每道测试题的单题评估结果
  started_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at              TIMESTAMPTZ,
  status                TEXT NOT NULL DEFAULT 'in_progress',  -- in_progress / completed / abandoned
  CONSTRAINT dl_sessions_state_check CHECK (state IN (
    'INITIALIZING','TEACHING','QUESTIONING','EVALUATING','AWAITING_COMMAND',
    'AI_ASSESSING_READINESS','CONFIRMING_TEST','TESTING','EVALUATING_TEST',
    'CHOOSING_AFTER_FAIL','COMPLETED'
  )),
  CONSTRAINT dl_sessions_status_check CHECK (
    status IN ('in_progress','completed','abandoned')
  )
);

CREATE INDEX IF NOT EXISTS idx_dl_sessions_user_node_status
  ON deep_learn_sessions(user_id, node_id, status);

CREATE INDEX IF NOT EXISTS idx_dl_sessions_user_updated
  ON deep_learn_sessions(user_id, updated_at DESC);
```

### Phase 2/3 新增的表（先列出，Phase 1 不创建）

```sql
-- Phase 2：Episodic Memory（session 结束后写入摘要）
CREATE TABLE IF NOT EXISTS learning_session_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL,
  node_id             TEXT NOT NULL,
  plan_id             TEXT NOT NULL,
  session_id          UUID NOT NULL REFERENCES deep_learn_sessions(id),
  summary             TEXT,
  concepts_covered    JSONB NOT NULL DEFAULT '[]',
  weak_points         JSONB NOT NULL DEFAULT '[]',
  strong_points       JSONB NOT NULL DEFAULT '[]',
  test_score          REAL,
  passed              BOOLEAN NOT NULL DEFAULT FALSE,
  conversation_turns  INTEGER NOT NULL DEFAULT 0,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Phase 2：Long-term Memory（扩展 user_profiles）
ALTER TABLE user_profiles
  ADD COLUMN IF NOT EXISTS learning_style JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS mastered_concepts JSONB NOT NULL DEFAULT '[]';

-- Phase 2：Procedural Memory（有效教学模式）
CREATE TABLE IF NOT EXISTS teaching_patterns (
  user_id       UUID NOT NULL,
  pattern_key   TEXT NOT NULL,
  pattern_value TEXT NOT NULL,
  confidence    REAL NOT NULL DEFAULT 0.5,
  sample_count  INTEGER NOT NULL DEFAULT 1,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, pattern_key)
);

-- Phase 3：完成笔记存储
CREATE TABLE IF NOT EXISTS completion_notes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL,
  node_id     TEXT NOT NULL,
  session_id  UUID NOT NULL REFERENCES deep_learn_sessions(id),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### API Endpoints（Phase 1 全部 endpoint）

所有 endpoint 在 `prefix="/api/deep-learn"` 下，需 JWT auth。

| Method | Path | 用途 |
|--------|------|------|
| `POST` | `/sessions` | 创建或恢复 session（同一 user+node 仅一个 in_progress） |
| `GET`  | `/sessions/{session_id}` | 查询 session 完整状态（供前端刷新页面用） |
| `POST` | `/sessions/{session_id}/initialize` | SSE：触发 Teaching Agent 讲第一个概念（仅新 session 调用一次） |
| `POST` | `/sessions/{session_id}/message` | SSE：发送用户消息（普通回答或测试答题），状态机自动路由 |
| `POST` | `/sessions/{session_id}/command` | SSE：发送控制命令（continue/expand/skip/reteach/restart/confirm_test/not_ready） |

> 删除决定：原 `/submit-test`、`/restart`、`/generate-note`、`DELETE /restart` 不再单独存在。restart 走 `/command` 的 `restart` 命令；提交测试答案走 `/message`；笔记生成 Phase 3 再加。

### POST `/sessions` 请求与响应

**请求：**
```json
{"node_id": "<uuid 或 text id>", "plan_id": "<plan id>"}
```

**响应（创建或恢复都返回这个 schema）：**
```json
{
  "success": true,
  "data": {
    "session_id": "uuid",
    "state": "INITIALIZING",         // 新 session 是 INITIALIZING；恢复时是当前 state
    "is_resumed": false,
    "node_name": "KV Cache",
    "node_why": "学习这个的目的...",
    "what_list": ["概念1", "概念2", "概念3"],
    "concepts_status": {"0": "pending", "1": "pending", "2": "pending"},
    "weak_points": [],
    "current_concept_index": 0,
    "recent_turns": []               // 恢复时附带最近对话
  }
}
```

### SSE 消息格式（initialize / message / command 通用）

```jsonc
// 文本流式输出（Teaching Agent 讲解内容）
{"type": "chunk", "text": "KV Cache 做的事只有一件..."}

// 图（Phase 1 仅 mermaid）
{"type": "image_mermaid", "code": "graph LR\n  A-->B"}

// 状态变化（前端用于更新 UI）
{"type": "state_change", "from": "TEACHING", "to": "QUESTIONING"}

// 题目（与 chunk 解耦发送，便于前端结构化显示）
{"type": "questions", "items": ["题目1", "题目2", "题目3"]}

// 单题评估结果
{"type": "assessment", "is_correct": true, "explanation": "...", "feedback": "..."}

// 概念状态更新
{"type": "concept_update", "index": 1, "status": "done"}

// 进入"等待控制命令"状态
{"type": "show_commands", "commands": ["continue", "expand", "skip", "reteach"]}

// 综合判定准备好测试，让用户确认
{"type": "test_confirm_prompt", "message": "...", "commands": ["confirm_test", "not_ready"]}

// 测试未通过的选项
{"type": "fail_options", "message": "...", "options": [
  {"command": "restart", "label": "🔄 重新开始"},
  {"command": "not_ready", "label": "📚 针对弱点复习"}
]}

// 节点通过测试
{"type": "node_completed", "node_id": "..."}

// restart 命令的特殊响应
{"type": "restart", "new_session_id": "..."}

// 错误
{"type": "error", "error": {"code": "...", "message": "..."}}

// 单次 SSE 流结束（所有 endpoint 必须发）
{"type": "done"}
```

---

## 八、新增 LLM Configs

```
services/llm/configs/
  deep_learn_teaching.json              # Phase 1: Teaching Agent
  deep_learn_assessment_per_question.json  # Phase 1: 单题评估 schema
  deep_learn_assessment_overall.json    # Phase 1: 综合判定 schema（readiness + 测试通过）
  deep_learn_image_trigger.json         # Phase 2: 独立 Image Trigger Agent（Phase 1 内置于 teaching）
  deep_learn_note_gen.json              # Phase 3: Note Generator
  deep_learn_memory_update.json         # Phase 2: Memory Update Agent
```

> 命名约定：每个 JSON 文件包含 `model_params`（temperature/max_tokens/可选 model）和 `system_prompt` 两个顶层字段，沿用现有 `services/llm/configs/*.json` 的结构。

---

## 九、分阶段实施计划

### Phase 1：MVP（预计 3-4 周）

核心目标：**能跑通完整教学循环 + 3 题测试 + 节点标记**

**后端：**
- [ ] 在 Supabase 创建 `deep_learn_sessions` 表（按第七章 SQL 直接执行）
- [ ] Session 仓储层（CRUD + 每 3 轮 checkpoint recent_turns 写入）
- [ ] Session Orchestrator（代码状态机，11 个状态，按第三章转换表实现）
- [ ] Teaching Agent（接入教学 prompt，注入 short-term memory，5 种模式：normal/expand/reteach/probe_stuck/review_weak）
- [ ] Assessment Agent · 单题评估（含连续 2 次答错触发 probe_stuck）
- [ ] Assessment Agent · 综合判定（readiness + 测试通过判定共享 schema，prompt 内区分场景）
- [ ] SSE endpoints：`/sessions`、`/initialize`、`/message`、`/command`
- [ ] 测试通过后更新 `nodes.status = 'learned'`，session.status = 'completed'
- [ ] Session resume：同一 user+node 仅一个 in_progress，存在则恢复

**前端：**
- [ ] 新路由 `/deep-learn/:planId/:nodeId`
- [ ] 左右分栏布局（左：导航 + 概念列表 + 弱点追踪；右：对话区）
- [ ] 概念进度列表（✓ 已完成 / → 当前 / ○ 待学 / ⊘ 已跳过）
- [ ] 对话区（Markdown 渲染 + 控制按钮：继续/展开/跳过/重讲）
- [ ] 基础 Mermaid 图嵌入对话流渲染

### Phase 2：记忆系统 + 图片 + 笔记弹窗（4-6 周）

- [ ] 四种 Memory 完整实现（Long-term / Episodic / Procedural）
- [ ] Memory Update Agent（事件触发 + 3-5 session 后统计归纳）
- [ ] Memory Context Block 注入教学流程
- [ ] OpenRouter GPT-Image-2 接入（image_type == "dalle" 时调用）
- [ ] 图片钉图功能（左侧辅助对照区）
- [ ] KaTeX 数学公式渲染
- [ ] 笔记弹窗（左下角入口 + Markdown 实时编辑 + 自动采集关键定义）

### Phase 3：完成笔记 + PDF 导出 + 精调（后续）

- [ ] Note Generator Agent（混合方案：标准内容 + 个人学习轨迹）
- [ ] 知乎风格笔记渲染页面（专用排版）
- [ ] PDF 导出（Print CSS + `window.print()`，按需升级 Puppeteer）
- [ ] Procedural Memory 统计归纳（达到 3-5 次 session 自动触发）
- [ ] Multi-Agent `what` 列表改造上线后，工作台自动受益（无需额外改动）

---

## 十、已确认决策汇总

| 决策点 | 结论 |
|--------|------|
| 图片生成接入 | OpenRouter credit 调用 `gpt-image-2`，接入现有 `openai_compatible.py` provider |
| Phase 1 课程内容来源 | 直接使用节点现有 `what` 列表，Teaching Agent 自行展开每个主题 |
| Multi-Agent 改造 | 独立分支并行推进，改造后 `what` 列表质量提升，工作台体验自动变好 |
| 完成笔记范围 | 私人复习用，不支持公开分享 |
| 完成笔记 PDF 导出 | Phase 3 实现，方案：浏览器 Print CSS + `window.print()`，视需求升级 Puppeteer |
| Memory Update 模式 | **模式 C：重要事件触发 + session 结束兜底** |
| 用户异常关闭标签页 | 不影响 Memory Update，`deep_learn_sessions` 表已持久化 session 状态，下次打开直接 resume |
| Short-term 持久化频率 | 每 3 轮对话 checkpoint 一次写入 DB |
| Procedural Memory 更新频率 | 积累 3-5 次 session 后统计归纳一次 |
| 测试通过标准 | AI 综合判断，无固定分数线，由 Assessment Agent prompt 约束判断标准 |

---

## 十一、Memory Update 模式 C 详细规则

### 触发时机

| 事件 | 更新内容 |
|------|---------|
| 用户通过某概念的题目 | Long-term：标记该子概念已掌握 |
| 用户连续两次答错同一概念 | Short-term：更新 `weak_points`；Long-term：记录弱点 |
| 用户跳过某概念 | Short-term：标记为 skipped，不计入掌握 |
| 测试通过 | Episodic：写入完整 session 摘要；Long-term：更新已掌握概念列表 |
| 测试未通过 | Episodic：写入 session 摘要（含弱点分析） |
| 每 3 轮对话 | Short-term：checkpoint 写入 `deep_learn_sessions.recent_turns` |
| 每 3-5 次 session 完成 | Procedural：Memory Update Agent 统计归纳有效教学模式 |

### 用户关闭标签页的处理

```
用户关闭标签页
    │
    └── deep_learn_sessions 表已有最新状态（每 3 轮写一次）
        ├── 重要事件（答对/错/跳过）已实时写入
        └── 下次打开 → Session Orchestrator 检测到 in_progress session → 直接 resume
```

不需要 `beforeunload` 复杂逻辑，Mode C 的事件触发覆盖了所有有意义的状态变化。

---

## 十二、Assessment Agent Prompt 约束（综合判定 schema 专用）

> 此约束仅适用于 **综合判定 schema** 调用（readiness check + 3 题答完后的最终通过判定）。单题评估使用 schema A，由单独 prompt 控制（侧重当题对错与即时反馈）。

```
判断标准（严格按此执行）：

通过信号：
  - 能用自己的话正确解释核心概念（不是机械复述）
  - 能识别常见误区并说明为什么错
  - 对应用场景的判断基本正确

不通过信号：
  - 机械复述原话，无法用例子说明
  - 对核心概念存在明显混淆且经提示后仍未纠正
  - 关键步骤/原理答错且无法从 feedback 中修正

边界情况：
  - 有小错误但整体心智模型正确 → passed=true，confidence 给 0.7-0.8
  - confidence < 0.6 时：
      - readiness 场景 → ready_for_test=false，给出 suggest_review_concepts
      - 测试通过场景 → passed=false（不强行判过）

输出格式（综合判定 schema，与第四章 "Assessment Agent · 综合判定" 对齐）：
{
  "passed": bool,
  "confidence": 0.0-1.0,
  "ready_for_test": bool,            // readiness 场景必填；测试场景可重复 passed 的值
  "reason": "一句话判定理由",
  "strong_areas": ["已掌握的概念"],
  "weak_areas": ["仍存在疑问的概念"],
  "suggest_review_concepts": []      // readiness 场景下，建议先复习的概念
}
```
