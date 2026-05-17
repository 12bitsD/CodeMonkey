# PRD：深入学习工作台（Deep Learning Workspace）

> 版本：v0.2  
> 日期：2026-05-18  
> 状态：核心决策已确认，进入实施规划

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
[Memory Manager] 加载四种记忆，构建用户画像 context
    │
    ▼
Session Orchestrator 判断：是否有未完成 session？
    ├── 有 → 断点续学（从 session_state 恢复）
    └── 无 → 新建 session，进入初始化
    │
    ▼
[初始化] Teaching Agent 发出探测题，校准难度
    │
    ▼
循环：[讲解概念 N] → [出题] → [评估] → [等待指令]
    │                                        │
    │                               继续 / 展开 / 跳过 / 重讲
    │
    ▼
所有概念讲完（或跳过）
    │
    ▼
[Assessment Agent] 判断用户整体理解程度
    ├── 还不够 → 推荐针对弱点再讲一遍
    └── 差不多了 → "你对这个节点已有基本掌握，准备综合测试了吗？"
    │
    ▼
用户确认 → [综合测试] → [AI 判定]
    ├── 通过 → [生成完成笔记] → 节点标记为 learned
    └── 未通过 → 展示弱点 → 提示选择：重新开始 / 针对弱点复习
```

---

## 三、状态机设计

### 状态定义

| 状态 | 描述 |
|------|------|
| `INITIALIZING` | 加载 Memory，构建 context，发出难度探测题 |
| `PROBING` | 等待用户回答探测题，校准初始难度 |
| `TEACHING` | Teaching Agent 正在讲解当前概念 |
| `QUESTIONING` | 当前概念讲完，AI 出题，等待用户回答 |
| `EVALUATING` | Assessment Agent 评估用户回答质量 |
| `AWAITING_COMMAND` | 评估完毕，等待用户指令（继续/展开/跳过/重讲） |
| `AI_ASSESSING_READINESS` | 所有概念讲完，AI 判断是否准备好测试 |
| `CONFIRMING_TEST` | AI 询问"准备好测试了吗"，等待用户确认 |
| `TESTING` | 综合测试阶段，AI 出综合题，用户逐一作答 |
| `EVALUATING_TEST` | Assessment Agent 综合判定测试结果 |
| `CHOOSING_AFTER_FAIL` | 测试未通过，展示弱点，等待用户选择下一步 |
| `GENERATING_NOTE` | Note Generator Agent 生成完成笔记 |
| `COMPLETED` | 节点已掌握，笔记已生成 |

### 状态转换规则

```
INITIALIZING → PROBING                  : session 创建完成，探测题已发出
PROBING → TEACHING                      : 用户回答探测题，难度校准完成
TEACHING → QUESTIONING                  : 讲解内容输出完毕
QUESTIONING → EVALUATING                : 用户发送回答
EVALUATING → AWAITING_COMMAND           : 评估完成，同时更新 weak_points
AWAITING_COMMAND → TEACHING             : 用户说"继续"（下一概念）
AWAITING_COMMAND → TEACHING             : 用户说"展开"（深入当前概念）
AWAITING_COMMAND → TEACHING             : 用户说"跳过"（跳至下一概念，标记为 skipped）
AWAITING_COMMAND → TEACHING             : 用户说"重讲"（换角度重讲当前概念）
AWAITING_COMMAND → AI_ASSESSING_READINESS : 所有概念讲完时自动触发
AI_ASSESSING_READINESS → CONFIRMING_TEST  : AI 判断用户理解充分
AI_ASSESSING_READINESS → TEACHING        : AI 判断需要补讲弱点概念
CONFIRMING_TEST → TESTING               : 用户确认准备好
CONFIRMING_TEST → TEACHING              : 用户说还没准备好
TESTING → EVALUATING_TEST               : 用户完成所有测试题
EVALUATING_TEST → GENERATING_NOTE       : 通过
EVALUATING_TEST → CHOOSING_AFTER_FAIL   : 未通过，展示弱点分析
CHOOSING_AFTER_FAIL → INITIALIZING      : 用户选择"重新开始"
CHOOSING_AFTER_FAIL → TEACHING          : 用户选择"针对弱点复习"（跳至弱点概念）
GENERATING_NOTE → COMPLETED             : 笔记生成完毕
任意状态 → INITIALIZING                 : 用户手动点击"重新开始"
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
    ├─ 状态 == TEACHING / PROBING
    │       └── Teaching Agent（LLM，主教学流程）
    │               └── Image Trigger Agent（决定是否生图，输出 mermaid 或 dalle prompt）
    │
    ├─ 状态 == EVALUATING / EVALUATING_TEST / AI_ASSESSING_READINESS
    │       └── Assessment Agent（LLM，评估 + 校准难度 + 更新弱点）
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
- **Memory Context 注入**：每次调用前拼入四类记忆摘要
- **输出格式**：
  ```json
  {
    "content": "讲解文本（Markdown）",
    "needs_image": true,
    "image_type": "mermaid",
    "mermaid_code": "graph LR...",
    "dalle_prompt": null,
    "questions": ["题目1", "题目2", "陷阱题"],
    "is_concept_done": true
  }
  ```

#### Assessment Agent

- **输入**：当前概念、用户回答、本次 session 的 weak_points 历史
- **输出**：
  ```json
  {
    "is_correct": true,
    "quality_score": 0.7,
    "explanation": "理解了核心，但对边界情况不确定",
    "update_weak_points": ["Prefill 计算复杂度"],
    "difficulty_delta": -1,
    "wrong_count": 1
  }
  ```
- **综合评估时**额外输出 `{ "ready_for_test": true, "overall_understanding": "..." }`

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

## 七、后端设计

### 新增数据库表

```sql
-- Session 状态持久化（支持断点续学）
CREATE TABLE deep_learn_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'INITIALIZING',
  current_concept_index INTEGER DEFAULT 0,
  difficulty_level INTEGER DEFAULT 3,        -- 1-5
  wrong_count_current INTEGER DEFAULT 0,     -- 当前概念的连续错误次数
  concepts_status TEXT DEFAULT '{}',         -- JSON: {concept_name: "done"/"skipped"/"current"}
  weak_points TEXT DEFAULT '[]',             -- JSON: 弱点列表
  conversation_summary TEXT,                 -- 压缩的对话摘要（替代全量历史）
  recent_turns TEXT DEFAULT '[]',            -- JSON: 最近 8 轮对话（short-term memory）
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ended_at TIMESTAMP,
  status TEXT DEFAULT 'in_progress'          -- in_progress / completed / abandoned
);

-- Episodic Memory：每次 session 结束后写入摘要
CREATE TABLE learning_session_records (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  summary TEXT,                              -- AI 生成的 session 摘要
  concepts_covered TEXT DEFAULT '[]',        -- JSON
  weak_points TEXT DEFAULT '[]',             -- JSON
  strong_points TEXT DEFAULT '[]',           -- JSON
  test_score REAL,
  passed BOOLEAN DEFAULT FALSE,
  conversation_turns INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Long-term Memory：用户学习风格画像（扩展 user_profiles）
-- 在 user_profiles 表新增以下字段：
-- learning_style TEXT DEFAULT '{}'          -- JSON: {analogy_type, pace, preferred_depth}
-- mastered_concepts TEXT DEFAULT '[]'       -- JSON: 跨节点掌握概念清单

-- Procedural Memory：有效教学模式
CREATE TABLE teaching_patterns (
  user_id TEXT NOT NULL,
  pattern_key TEXT NOT NULL,                 -- e.g. "effective_analogy_type"
  pattern_value TEXT NOT NULL,
  confidence REAL DEFAULT 0.5,              -- 0-1，随样本增加
  sample_count INTEGER DEFAULT 1,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, pattern_key)
);

-- 完成笔记存储
CREATE TABLE completion_notes (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  content TEXT NOT NULL,                     -- Markdown 内容
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 新增 API Endpoints

```
# Session 管理
POST   /api/deep-learn/sessions                    创建或恢复 session
GET    /api/deep-learn/sessions/:sessionId         获取 session 状态
DELETE /api/deep-learn/sessions/:sessionId/restart 重置 session

# 核心交互（SSE 流式响应）
POST   /api/deep-learn/sessions/:sessionId/message 发送消息（含 AI 回复流）
POST   /api/deep-learn/sessions/:sessionId/command 发送控制命令（继续/展开/跳过/重讲）

# 测试
POST   /api/deep-learn/sessions/:sessionId/submit-test 提交测试答案

# 笔记
POST   /api/deep-learn/sessions/:sessionId/generate-note  生成完成笔记（SSE）
GET    /api/deep-learn/sessions/:sessionId/note           获取已生成的笔记
```

### SSE 消息格式（message endpoint）

```jsonc
// Teaching Agent 输出
{"type": "chunk", "text": "KV Cache 做的事只有一件..."}

// 图片触发
{"type": "image_mermaid", "code": "graph LR\n  A-->B"}
{"type": "image_dalle_start"}                            // 开始生成
{"type": "image_dalle_done", "url": "https://..."}      // 生成完成

// 状态变化
{"type": "state_change", "from": "TEACHING", "to": "QUESTIONING"}

// 题目
{"type": "questions", "items": ["题目1", "题目2", "陷阱题"]}

// 评估结果
{"type": "assessment", "is_correct": true, "explanation": "..."}

// 完成
{"type": "done"}
```

---

## 八、新增 LLM Configs

```
services/llm/configs/
  deep_learn_teaching.json      # Teaching Agent system prompt
  deep_learn_assessment.json    # Assessment Agent system prompt
  deep_learn_image_trigger.json # Image Trigger Agent system prompt
  deep_learn_note_gen.json      # Note Generator Agent system prompt
  deep_learn_memory_update.json # Memory Update Agent system prompt
```

---

## 九、分阶段实施计划

### Phase 1：MVP（预计 3-4 周）

核心目标：**能跑通完整教学循环 + 测试 + 节点标记**

**后端：**
- [ ] `deep_learn_sessions` 表和基础 CRUD（含每 3 轮 checkpoint 逻辑）
- [ ] Session Orchestrator（代码状态机，覆盖全部状态转换）
- [ ] Teaching Agent（接入教学 prompt，short-term memory 注入）
- [ ] Assessment Agent（答题评估 + 连续 2 次答错触发逻辑）
- [ ] SSE endpoints：`/message`、`/command`
- [ ] 测试通过后更新节点状态为 `learned`
- [ ] Session resume 逻辑（检测到 in_progress session 时自动恢复）

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

## 十二、Assessment Agent Prompt 约束

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
  - 有小错误但整体心智模型正确 → 通过
  - confidence < 0.6 时 → 不要强行判定，建议补测一题

输出格式：
{
  "passed": bool,
  "confidence": 0.0-1.0,
  "reason": "一句话判定理由",
  "strong_areas": ["已掌握的概念"],
  "weak_areas": ["仍存在疑问的概念"]
}
```
