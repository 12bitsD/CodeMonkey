# AI Coding Plan — 深入学习工作台 Phase 1

> 版本：v2.0（基于 PRD v0.3 完全重写）
> 适用：可被任何 AI coding agent 直接执行
> 设计原则：契约先行（Contract First）、原子任务、可验证、零隐式依赖

---

## Part 0 · Foundation（必读）

### 0.1 环境与代码库约定

| 约定 | 说明 |
|------|------|
| 数据库 | PostgreSQL on Supabase。DDL 直接在 Supabase SQL Editor 执行，**禁止**在 Python 代码里写 `CREATE TABLE` 或 migration 逻辑 |
| 后端 SQL 占位符 | 一律用 `?`，`database.DbSession.execute` 内部自动转 `%s` |
| JSON 字段写入 | 直接传 Python `dict`/`list`，`database._adapt_params` 会自动用 `psycopg2.extras.Json` 包装 |
| JSON 字段读出 | psycopg2 + `RealDictCursor` 已自动反序列化为 dict/list，**不要再 `json.loads`** |
| DB 访问 | FastAPI endpoint 用 `Depends(get_db)`；后台 / SSE 内部用 `with get_db_context() as db:` |
| LLM 调用 | `get_llm_client()` → `chat_json(system_prompt, user_prompt, temperature, max_tokens, model=None)` 返回 `dict` |
| LLM 流式 | `chat_stream(messages=[LLMMessage(role, content)], temperature, max_tokens, model)` 返回 `AsyncGenerator[str]` |
| LLM Config 加载 | 沿用现有 `services/llm/configs/__init__.py` 的 `load_ai_config(config_name, user_input, **kwargs)` 或直接读 JSON 文件 |
| Auth | `from utils.auth import get_current_user_id`，FastAPI `Depends(get_current_user_id)` 返回 user_id `str`（UUID 形式） |
| 错误响应 | `raise HTTPException(status_code=N, detail={"code": "X", "message": "Y"})`，全局 handler 会包装成 `{success: false, error: {...}}` |
| SSE 模式 | 参考 `routers/ai.py` 的 `_stream_chat`：`StreamingResponse(_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`，每条消息格式 `f"data: {json.dumps({...}, ensure_ascii=False)}\n\n"` |
| 前端 API base | `import { buildApiUrl } from '../config/api'`；token 用 `tokenManager.get()` from `services/api.js` |
| 前端 Markdown 渲染 | 复用 `components/chat/ChatMarkdownMessage.jsx` |

### 0.2 文件树（必须落在这些路径，不要新建目录）

```
backend/
├── models_deep_learn.py                                    [B-02]
├── services/
│   ├── deep_learn/
│   │   ├── __init__.py                                     [B-03]  空模块声明
│   │   ├── session_repo.py                                 [B-03]
│   │   ├── state_machine.py                                [B-04]
│   │   ├── agents/
│   │   │   ├── __init__.py                                 (空)
│   │   │   ├── teaching.py                                 [B-05]
│   │   │   ├── assessment_per_question.py                  [B-06]
│   │   │   └── assessment_overall.py                       [B-07]
│   │   └── service.py                                      [B-08]
│   └── llm/configs/
│       ├── deep_learn_teaching.json                        [B-05]
│       ├── deep_learn_assessment_per_question.json         [B-06]
│       └── deep_learn_assessment_overall.json              [B-07]
├── routers/
│   └── deep_learn.py                                       [B-09]
└── main.py                                                 [B-10] 修改

frontend/src/
├── services/
│   └── deepLearnApi.js                                     [F-01]
├── hooks/
│   └── useDeepLearnSession.js                              [F-02]
├── pages/
│   └── DeepLearnPage.jsx                                   [F-04]
├── components/
│   └── deep-learn/
│       ├── ConceptProgress.jsx                             [F-05]
│       ├── DeepLearnChat.jsx                               [F-06]
│       ├── CommandBar.jsx                                  [F-07]
│       └── MermaidDiagram.jsx                              [F-07]
└── App.jsx                                                 [F-03] 修改
```

### 0.3 类型契约（Single Source of Truth）

> 这是**所有任务**的契约。后续所有任务的字段名、类型、可空性必须与此完全一致。任何不一致都是 bug。

#### 0.3.1 枚举

```python
# 13 个值在第三章列出，这里全部必须实现
DeepLearnState = Literal[
    "INITIALIZING", "TEACHING", "QUESTIONING", "EVALUATING", "AWAITING_COMMAND",
    "AI_ASSESSING_READINESS", "CONFIRMING_TEST", "TESTING", "EVALUATING_TEST",
    "CHOOSING_AFTER_FAIL", "COMPLETED",
]

DeepLearnCommand = Literal[
    "continue", "expand", "skip", "reteach",
    "restart", "confirm_test", "not_ready",
]

ConceptStatus = Literal["pending", "current", "done", "skipped"]

SessionStatus = Literal["in_progress", "completed", "abandoned"]

TeachingMode = Literal["normal", "expand", "reteach", "probe_stuck", "review_weak"]
```

#### 0.3.2 数据库行 → Python 对象（`SessionState`）

```python
class SessionState(BaseModel):
    id: str                              # UUID 字符串
    user_id: str                         # UUID 字符串
    node_id: str
    plan_id: str
    state: DeepLearnState
    current_concept_index: int           # 0-based
    difficulty_level: int                # 1..5
    wrong_count_current: int             # 0..N
    concepts_status: dict[str, str]      # {"0": "done", "1": "current", ...} index 为字符串
    weak_points: list[str]               # ["概念名"]
    recent_turns: list[dict]             # [{"role":"user|assistant", "content":"..."}]
    what_list: list[str]                 # session 创建时的快照
    test_questions: list[str]            # 3 道测试题，CONFIRMING_TEST → TESTING 时填充
    test_current_index: int              # 0..2
    test_results: list[dict]             # 单题评估结果列表，长度 == 已答测试题数
    status: SessionStatus
    # 时间戳字段保留 raw 即可，前端不直接用
```

#### 0.3.3 LLM Agent 输出契约（严格 JSON）

```python
# Teaching Agent — 任何 mode 都返回同一 schema
class TeachingOutput(BaseModel):
    content: str                          # Markdown 文本，必填非空
    questions: list[str]                  # normal/expand/reteach 模式下 2-3 条；probe_stuck 模式下可为空
    needs_image: bool = False
    image_type: Optional[str] = None      # Phase 1 仅 "mermaid" 或 None
    mermaid_code: Optional[str] = None

# Assessment - 单题评估
class AssessmentPerQuestionOutput(BaseModel):
    is_correct: bool
    quality_score: float                  # 0..1
    explanation: str                      # 鼓励性反馈，展示给用户
    feedback: str                         # 具体偏差点
    update_weak_points: list[str] = []
    difficulty_delta: int = 0             # -1 | 0 | 1
    wrong_count: int = 0                  # 当前概念的累计错误次数（agent 算好，service 直接采用）

# Assessment - 综合判定
class AssessmentOverallOutput(BaseModel):
    passed: bool
    confidence: float                     # 0..1
    ready_for_test: bool                  # readiness 场景必填；测试场景 = passed
    reason: str
    strong_areas: list[str] = []
    weak_areas: list[str] = []
    suggest_review_concepts: list[str] = []
```

#### 0.3.4 API 请求/响应

```python
# POST /api/deep-learn/sessions
class CreateSessionRequest(BaseModel):
    node_id: str
    plan_id: str

class CreateSessionData(BaseModel):
    session_id: str
    state: DeepLearnState
    is_resumed: bool
    node_name: str
    node_why: str
    what_list: list[str]
    concepts_status: dict[str, str]
    weak_points: list[str]
    current_concept_index: int
    recent_turns: list[dict]              # 仅 resume 时非空

# 响应 = {"success": True, "data": CreateSessionData(...)}

# POST /api/deep-learn/sessions/{id}/message
class MessageRequest(BaseModel):
    content: str

# POST /api/deep-learn/sessions/{id}/command
class CommandRequest(BaseModel):
    command: DeepLearnCommand
```

### 0.4 SSE 事件目录（Single Source of Truth）

> 所有 SSE endpoint（initialize / message / command）发出的事件**仅限**以下类型。前端 hook 也仅识别这些类型。任何其他事件 = bug。

```jsonc
// === 流式文本 ===
{"type": "chunk", "text": "string"}                            // Teaching Agent 讲解内容；按段或整段一次性发，Phase 1 无 token-level streaming

// === 图 ===
{"type": "image_mermaid", "code": "graph LR\nA-->B"}           // Teaching Agent 输出 mermaid 时立即发

// === 状态变化（前端用于驱动 UI 切换） ===
{"type": "state_change", "from": "TEACHING", "to": "QUESTIONING"}

// === 概念进度更新 ===
{"type": "concept_update", "index": 1, "status": "done"}        // index 为字符串化时按整数转字符串

// === 题目（与 chunk 解耦，前端可单独列表展示） ===
{"type": "questions", "items": ["题目1", "题目2", "题目3"]}

// === 单题评估结果 ===
{"type": "assessment", "is_correct": true, "explanation": "...", "feedback": "..."}

// === 等待控制命令（前端高亮按钮） ===
{"type": "show_commands", "commands": ["continue", "expand", "skip", "reteach"]}

// === readiness 确认 ===
{"type": "test_confirm_prompt", "message": "...", "commands": ["confirm_test", "not_ready"]}

// === 测试未通过的选项 ===
{"type": "fail_options", "message": "...", "options": [
  {"command": "restart", "label": "🔄 重新开始"},
  {"command": "not_ready", "label": "📚 针对弱点复习"}
]}

// === 节点通过 ===
{"type": "node_completed", "node_id": "..."}

// === restart 命令的响应：后端已开新 session ===
{"type": "restart", "new_session_id": "..."}

// === 错误 ===
{"type": "error", "error": {"code": "...", "message": "..."}}

// === 流结束（每个 SSE response 必须发） ===
{"type": "done"}
```

### 0.5 状态机转换表（Single Source of Truth）

> 状态机由 Service 层驱动，**不**调用 LLM。函数 `decide_next(state, event, ctx) → Decision` 实现下表。

| 当前状态 | 事件 | 上下文条件 | 动作 (action) | 下一状态 |
|---------|------|----------|--------------|---------|
| INITIALIZING | `init` | — | `teach(mode=normal, index=0)` | TEACHING |
| TEACHING | `agent_output_done` | output 含 questions | `emit_questions` | QUESTIONING |
| TEACHING | `agent_output_done` | output 无 questions（probe_stuck） | `wait_user` | QUESTIONING |
| QUESTIONING | `user_message` | — | `assess_per_question` | EVALUATING |
| EVALUATING | `assess_done` | is_correct=true | `mark_concept_done + show_commands` | AWAITING_COMMAND |
| EVALUATING | `assess_done` | is_correct=false, wrong_count<2 | `show_commands` | AWAITING_COMMAND |
| EVALUATING | `assess_done` | is_correct=false, wrong_count>=2 | `teach(mode=probe_stuck)` | TEACHING |
| AWAITING_COMMAND | `cmd:continue` | has_next_concept | `advance + teach(mode=normal)` | TEACHING |
| AWAITING_COMMAND | `cmd:continue` | !has_next_concept | `check_readiness` | AI_ASSESSING_READINESS |
| AWAITING_COMMAND | `cmd:expand` | — | `teach(mode=expand)` | TEACHING |
| AWAITING_COMMAND | `cmd:skip` | has_next_concept | `mark_skipped + advance + teach(mode=normal)` | TEACHING |
| AWAITING_COMMAND | `cmd:skip` | !has_next_concept | `mark_skipped + check_readiness` | AI_ASSESSING_READINESS |
| AWAITING_COMMAND | `cmd:reteach` | — | `teach(mode=reteach)` | TEACHING |
| AI_ASSESSING_READINESS | `readiness_done` | ready_for_test=true | `show_test_confirm` | CONFIRMING_TEST |
| AI_ASSESSING_READINESS | `readiness_done` | ready_for_test=false | `teach(mode=review_weak)` | TEACHING |
| CONFIRMING_TEST | `cmd:confirm_test` | — | `generate_test_questions + emit_first` | TESTING |
| CONFIRMING_TEST | `cmd:not_ready` | — | `teach(mode=review_weak)` | TEACHING |
| TESTING | `user_message` | — | `assess_per_question(test_mode)` | EVALUATING_TEST |
| EVALUATING_TEST | `assess_done` | test_current_index < 2 | `advance_test + emit_next_test_q` | TESTING |
| EVALUATING_TEST | `assess_done` | test_current_index == 2 | `final_judge` | (分支 ↓) |
| (final_judge) | passed=true | — | `mark_node_learned` | COMPLETED |
| (final_judge) | passed=false | — | `show_fail_options` | CHOOSING_AFTER_FAIL |
| CHOOSING_AFTER_FAIL | `cmd:restart` | — | `abandon + create_new_session` | INITIALIZING(新) |
| CHOOSING_AFTER_FAIL | `cmd:not_ready` | — | `teach(mode=review_weak)` | TEACHING |
| 任意状态 | `cmd:restart` | — | `abandon + create_new_session` | INITIALIZING(新) |

`has_next_concept` = `current_concept_index + 1 < len(what_list)`

---

## Part 1 · Backend Tasks

### B-01：建库表

**Goal**：在 Supabase 创建 `deep_learn_sessions` 表。

**操作**：将下方 SQL 复制粘贴到 Supabase 项目的 SQL Editor 执行。

```sql
CREATE TABLE IF NOT EXISTS deep_learn_sessions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL,
  node_id               TEXT NOT NULL,
  plan_id               TEXT NOT NULL,
  state                 TEXT NOT NULL DEFAULT 'INITIALIZING',
  current_concept_index INTEGER NOT NULL DEFAULT 0,
  difficulty_level      INTEGER NOT NULL DEFAULT 3,
  wrong_count_current   INTEGER NOT NULL DEFAULT 0,
  concepts_status       JSONB NOT NULL DEFAULT '{}'::jsonb,
  weak_points           JSONB NOT NULL DEFAULT '[]'::jsonb,
  recent_turns          JSONB NOT NULL DEFAULT '[]'::jsonb,
  what_list             JSONB NOT NULL DEFAULT '[]'::jsonb,
  test_questions        JSONB NOT NULL DEFAULT '[]'::jsonb,
  test_current_index    INTEGER NOT NULL DEFAULT 0,
  test_results          JSONB NOT NULL DEFAULT '[]'::jsonb,
  conversation_summary  TEXT,
  started_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at              TIMESTAMPTZ,
  status                TEXT NOT NULL DEFAULT 'in_progress',
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

**Verify**：在 SQL Editor 跑 `SELECT * FROM deep_learn_sessions LIMIT 1;`，应返回空结果但无错误。

---

### B-02：Pydantic Models

**File**：`backend/models_deep_learn.py`

**Goal**：把 0.3 的所有类型契约转成 Pydantic 模型。

**实现要点**：
- 用 `Literal` 类型而非 `Enum`，避免后续序列化烦恼
- `SessionState` 是数据传输对象，**不**做任何业务校验
- 所有 model 用 `from pydantic import BaseModel, Field`
- 文件顶端：`from __future__ import annotations`

**必须导出的符号**（其他文件会 import）：
```
DeepLearnState, DeepLearnCommand, ConceptStatus, SessionStatus, TeachingMode,
SessionState,
TeachingOutput, AssessmentPerQuestionOutput, AssessmentOverallOutput,
CreateSessionRequest, CreateSessionData,
MessageRequest, CommandRequest
```

**Verify**：`python -c "from models_deep_learn import SessionState; print(SessionState.model_fields.keys())"` 能列出 0.3.2 全部 14 个字段。

---

### B-03：Session Repository

**File**：`backend/services/deep_learn/session_repo.py`

**Goal**：封装 `deep_learn_sessions` 表的所有数据库访问。**不包含业务逻辑**。

**导出函数签名（必须完全匹配）**：

```python
def get_active_session(db: DbSession, user_id: str, node_id: str) -> Optional[SessionState]:
    """查 user+node 下唯一 in_progress session。SQL: WHERE user_id=? AND node_id=? AND status='in_progress' ORDER BY updated_at DESC LIMIT 1"""

def get_session_by_id(db: DbSession, session_id: str, user_id: str) -> Optional[SessionState]:
    """根据 id 取，并验证 user_id 匹配（防越权）"""

def create_session(
    db: DbSession, *, user_id: str, node_id: str, plan_id: str, what_list: list[str],
) -> SessionState:
    """INSERT...RETURNING *。concepts_status 初始化为 {"0":"pending","1":"pending",...}（用 index 字符串做 key）"""

def update_session(db: DbSession, session_id: str, **fields) -> None:
    """部分更新。允许的字段白名单（其他字段静默忽略）：
       state, current_concept_index, difficulty_level, wrong_count_current,
       concepts_status, weak_points, recent_turns, conversation_summary,
       test_questions, test_current_index, test_results,
       ended_at, status
       SQL 动态拼接 SET 子句，updated_at = NOW() 始终自动加。"""

def abandon_session(db: DbSession, session_id: str) -> None:
    """快捷封装：update_session(db, id, status='abandoned', ended_at=NOW())"""
```

**实现要点**：
- 使用 `RealDictCursor`（已是默认）；行字段直接 `row["concepts_status"]` 即是 dict，**不要**再 `json.loads`
- `_row_to_state(row)` 内部辅助函数：把数据库行转成 `SessionState`
- `created_at`/`updated_at`/`ended_at`/`started_at` 不放进 `SessionState`（前端用不到，避免序列化麻烦）
- 每个写入函数调用 `db.commit()`（FastAPI Depends 的 session 由 endpoint 调用方负责，但本仓储为了让 SSE 中途 commit 方便，自己 commit；这不会破坏事务因为我们不在显式 transaction 里）

**Verify**：写一个临时脚本，依次调用 create_session → get_active_session → update_session(state='TEACHING') → get_session_by_id，每步结果与预期一致。

---

### B-04：状态机（核心 · 纯函数）

**File**：`backend/services/deep_learn/state_machine.py`

**Goal**：把 0.5 节的转换表实现为纯函数。**不调用 LLM**，**不访问数据库**，只做逻辑判断。

**导出的核心 API**：

```python
@dataclass
class Decision:
    next_state: DeepLearnState
    action: Literal[
        "teach", "wait_user", "emit_questions",
        "assess_per_question", "show_commands",
        "check_readiness", "show_test_confirm",
        "generate_test_questions", "emit_next_test_q",
        "final_judge", "mark_node_learned", "show_fail_options",
        "abandon_and_restart",
    ]
    # action 的参数：
    teach_mode: Optional[TeachingMode] = None      # action == "teach" 时填
    advance_concept: bool = False                   # 是否在动作前递增 current_concept_index
    mark_skipped: bool = False                      # 是否把当前概念标 skipped
    # final_judge 的输入由 service 层根据 test_results 自行 aggregate

def decide_on_init() -> Decision: ...

def decide_on_user_message(
    state: DeepLearnState,
    wrong_count: int,
    is_test_phase: bool,    # state == TESTING 时为 True
) -> Decision: ...

def decide_on_assessment_done(
    state: DeepLearnState,             # EVALUATING 或 EVALUATING_TEST
    is_correct: bool,
    new_wrong_count: int,
    test_current_index: int,           # 仅在 test 阶段有意义
    test_total: int = 3,
    all_concepts_done: bool = False,
) -> Decision: ...

def decide_on_readiness_done(ready_for_test: bool) -> Decision: ...

def decide_on_command(
    state: DeepLearnState,
    command: DeepLearnCommand,
    current_concept_index: int,
    what_list_len: int,
    all_concepts_done: bool,
) -> Decision: ...

def decide_on_final_judge(passed: bool) -> Decision: ...
```

**实现要点**：
- 严格按 0.5 表对应；不要"聪明"添加表外转换
- 不合法的 (state, event) 组合：返回 `Decision(next_state=state, action="wait_user")` 并让 service 层记 warning log。**不要 raise**（SSE 中 raise 难处理）
- `cmd:restart` 在任何状态都返回 `Decision(next_state="INITIALIZING", action="abandon_and_restart")`

**Verify（必跑）**：写一个 `backend/tests/unit/test_deep_learn_state_machine.py`，逐行验证 0.5 表里的每个分支至少一个用例。这个测试**必须能离线运行**（不需要 DB、不需要 LLM），是整个 Phase 1 唯一强制单元测试。

---

### B-05：Teaching Agent

**File A**：`backend/services/llm/configs/deep_learn_teaching.json`

```json
{
  "model_params": { "temperature": 0.6, "max_tokens": 2048 },
  "system_prompt": "你是一位专业的 1v1 AI 家教，严格遵守以下教学原则。\n\n【原则一·工作记忆保护】每次只讲一个概念。若该概念包含超过 3 个子概念，先给 2-3 句 overview，再逐个展开，每组不超过 3 个。每多写一句先问：「去掉它，理解会受损吗？」不会则删。\n\n【原则二·认知锚定】讲任何概念前，先一句话说清楚「它在做什么 / 为什么需要它」，再给 formal 定义。每个新概念出现时，先说它和前面讲过的是什么关系（依赖/对比/推广/特例）。\n\n【原则三·逻辑连续性】每段第一句是结论，后面跟推导或论据。每句话写完，下一句必须回答上一句引发的问号。段落内句子之间必须有因果/推演关系，禁止突然引入新内容。\n\n【原则四·不主动延伸】讲完一个知识点就停，不主动引入未讲过的新内容。可以回指已学内容，禁止前指未学内容。\n\n【输出格式】仅返回合法 JSON，不要 markdown 代码块包装：\n{\n  \"content\": \"讲解文本（中文 Markdown）\",\n  \"questions\": [\"题1\", \"题2\", \"题3\"],\n  \"needs_image\": false,\n  \"image_type\": null,\n  \"mermaid_code\": null\n}\n\n【题目要求】normal/expand/reteach 模式：3 道题（概念理解 + 应用 + 误区陷阱）。probe_stuck 模式：questions 必须是空数组，content 只问一个澄清问题（如「你在哪一步开始觉得不对劲？」），不给答案。"
}
```

**File B**：`backend/services/deep_learn/agents/teaching.py`

```python
class TeachingAgent:
    def __init__(self) -> None: ...

    async def run(
        self, *,
        node_name: str,
        node_why: str,
        current_concept: str,
        concept_index: int,
        total_concepts: int,
        difficulty_level: int,
        weak_points: list[str],
        recent_turns: list[dict],          # 最近 6-8 条 {role, content}
        mode: TeachingMode,
    ) -> TeachingOutput: ...
```

**实现要点**：
- 把 `system_prompt` 从 JSON 读出（直接 `json.load`，**不**用 `load_ai_config`，因为后者会加多余的 "Output Format" 段）
- `user_prompt` 由以下信息拼接（必须严格按此顺序）：
  ```
  [节点] {node_name}
  [学习目的] {node_why}
  [当前概念] {current_concept}（第 {concept_index+1} 个，共 {total_concepts} 个）
  [当前难度] {difficulty_level}/5
  [已识别弱点] {", ".join(weak_points) or "无"}
  [最近对话]
  {format_recent_turns(recent_turns)}

  [本次模式] {mode_instruction(mode)}
  ```
- `mode_instruction` 映射：
  | mode | 指令文本 |
  |------|---------|
  | normal | "按标准节奏讲解当前概念，然后出 3 道题。" |
  | expand | "对当前概念进行更深入展开，补充细节和边界情况，然后出 3 道更深的题。" |
  | reteach | "换一个全新的角度或类比重新讲解当前概念，不要重复之前的表述。" |
  | probe_stuck | "用户连续答错。不要继续给答案。只问一个澄清问题（你在哪一步卡住？），questions 字段返回空数组。" |
  | review_weak | "用户还没准备好测试。重点复习以下弱点：{weak_points}。出题侧重弱点。" |
- 调 `get_llm_client().chat_json(system_prompt, user_prompt, temperature=0.6, max_tokens=2048)` → `dict` → `TeachingOutput(**dict)`
- 如果 LLM 输出无法解析为合法 `TeachingOutput`，**重试一次**，仍失败则返回 `TeachingOutput(content="抱歉，AI 生成内容时遇到问题，请稍后重试。", questions=[])`，并写 error log

**Verify**：mock LLM 返回固定 JSON，断言函数返回正确 `TeachingOutput`。

---

### B-06：Assessment Agent · 单题评估

**File A**：`backend/services/llm/configs/deep_learn_assessment_per_question.json`

```json
{
  "model_params": { "temperature": 0.3, "max_tokens": 800 },
  "system_prompt": "你是学习评估专家。根据用户对一道题的回答，做出准确、严格但鼓励性的单题评估。\n\n【评估标准】\n通过：能用自己的话正确解释，能识别常见误区，能正确判断应用场景。\n不通过：机械复述、对核心概念明显混淆且未自我纠正、关键步骤答错且无法从反馈中修正。\n边界：有小错但整体心智模型正确 → is_correct=true，quality_score 给 0.7。\n\n【输出 JSON，不要 markdown 代码块】\n{\n  \"is_correct\": true,\n  \"quality_score\": 0.85,\n  \"explanation\": \"一句话评价，给用户看（鼓励性）\",\n  \"feedback\": \"具体指出哪里对哪里有偏差\",\n  \"update_weak_points\": [],\n  \"difficulty_delta\": 0,\n  \"wrong_count\": 0\n}\n\n【字段语义】\nwrong_count: 如果 is_correct=false，返回 (传入的 prev_wrong_count + 1)；否则返回 0。\ndifficulty_delta: -1（题答得吃力）/ 0（正常）/ 1（答得过于轻松）。\nupdate_weak_points: 用户暴露的新弱点（具体子概念名），若无返回 []。"
}
```

**File B**：`backend/services/deep_learn/agents/assessment_per_question.py`

```python
class AssessmentPerQuestionAgent:
    async def run(
        self, *,
        concept: str,
        question: str,
        user_answer: str,
        prev_wrong_count: int,
        weak_points: list[str],
    ) -> AssessmentPerQuestionOutput: ...
```

**实现要点**：
- `user_prompt` 拼接：
  ```
  [概念] {concept}
  [题目] {question}
  [用户回答] {user_answer}
  [当前累计错误次数] {prev_wrong_count}
  [已记录弱点] {weak_points}
  ```
- 校验：`quality_score` 必须 ∈ [0,1]，越界用 `max(0.0, min(1.0, x))` clamp
- 校验：`difficulty_delta` 必须 ∈ {-1, 0, 1}，否则置 0
- LLM 失败的兜底：`AssessmentPerQuestionOutput(is_correct=False, quality_score=0.0, explanation="评估暂不可用", feedback="", wrong_count=prev_wrong_count + 1)`

**Verify**：mock LLM 输出，测试三种情况：正确答案、错误答案（递增 wrong_count）、LLM 故障兜底。

---

### B-07：Assessment Agent · 综合判定

**File A**：`backend/services/llm/configs/deep_learn_assessment_overall.json`

```json
{
  "model_params": { "temperature": 0.3, "max_tokens": 1024 },
  "system_prompt": "你是严格的学习评估专家。在两种场景下用同一 schema 输出综合判定：\n\n场景 A（readiness）：用户已学完该节点所有/大部分概念，判断是否准备好做综合测试。\n场景 B（test）：用户已答完 3 道综合测试题，判断是否真正掌握该节点。\n\n【共同判定标准】\n通过：自己的话正确解释核心 + 识别常见误区 + 应用场景判断正确。\n不通过：机械复述 / 核心概念明显混淆且未纠正 / 关键步骤错且无法修正。\n边界：小错但整体心智模型正确 → passed=true，confidence 0.7-0.8。\nconfidence < 0.6：场景 A → ready_for_test=false；场景 B → passed=false。\n\n【输出 JSON，不要 markdown 代码块】\n{\n  \"passed\": true,\n  \"confidence\": 0.85,\n  \"ready_for_test\": true,\n  \"reason\": \"一句话\",\n  \"strong_areas\": [\"\"],\n  \"weak_areas\": [\"\"],\n  \"suggest_review_concepts\": []\n}\n\nready_for_test：场景 A 必填真值；场景 B 直接等于 passed。"
}
```

**File B**：`backend/services/deep_learn/agents/assessment_overall.py`

```python
class AssessmentOverallAgent:
    async def run_readiness(
        self, *,
        node_name: str,
        concepts_done: list[str],
        concepts_skipped: list[str],
        weak_points: list[str],
    ) -> AssessmentOverallOutput: ...

    async def run_final_judge(
        self, *,
        node_name: str,
        test_qa_pairs: list[dict],         # [{"question": "...", "answer": "...", "is_correct": bool, "feedback": "..."}, ...]
        weak_points: list[str],
    ) -> AssessmentOverallOutput: ...
```

**实现要点**：
- 两个方法共享 JSON config 的 system_prompt
- `user_prompt` 用 `[场景标识]` 区分场景 A/B（让 LLM 知道用 ready_for_test 还是 passed 作为主信号）
- 兜底：`AssessmentOverallOutput(passed=False, confidence=0.0, ready_for_test=False, reason="评估服务暂不可用")`

**Verify**：mock 两种场景的 LLM 输出。

---

### B-08：Deep Learn Service（最大文件 · 协调层）

**File**：`backend/services/deep_learn/service.py`

**Goal**：协调 state machine、agents、repo，提供给 router 的三个高层 API。

**导出 API**：

```python
class DeepLearnService:
    def __init__(self): ...

    async def get_or_create_session(
        self, *, db: DbSession, user_id: str, node_id: str, plan_id: str,
    ) -> tuple[SessionState, dict]:
        """返回 (session, node_meta)
           node_meta = {"node_name": str, "node_why": str}
           - 查 active in_progress session：有则返回 (is_resumed=True)
           - 否则查 nodes 表拿到 what/why/name，what_list 取 nodes.what 字段（数据库已是 JSONB list），创建新 session
           - what_list 空时仍创建（前端会提示），不抛错
           注意：is_resumed 信息不在返回元组里，调用方根据 session 时间戳判断；本函数 idempotent
        """

    async def stream_initialize(
        self, session: SessionState, node_meta: dict,
    ) -> AsyncGenerator[str, None]:
        """新建 session 后调一次，触发讲第一个概念。
           只在 state == INITIALIZING 时合法；否则发 error 事件并 return
        """

    async def stream_message(
        self, session: SessionState, node_meta: dict, content: str,
    ) -> AsyncGenerator[str, None]:
        """处理用户文本消息，按状态机路由"""

    async def stream_command(
        self, session: SessionState, node_meta: dict, command: DeepLearnCommand,
    ) -> AsyncGenerator[str, None]:
        """处理控制命令，按状态机路由"""
```

**实现要点**：

1. **SSE 序列化辅助函数**：
   ```python
   def _sse(event_type: str, **data) -> str:
       return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"
   ```

2. **每次状态变化都发 `state_change` 事件**；service 在 update_session 之后立刻 yield。

3. **每个 SSE generator 末尾必须 yield `_sse("done")`**（即使中途出错也要 done）。

4. **错误处理**：所有 agent 调用包在 try/except，捕获后 yield `_sse("error", error={"code":"AI_ERROR","message":str(e)})` 然后 yield done。

5. **关键的"运行 action"逻辑**（用 if/elif 分发，不要 dict-dispatch，便于调试）：
   ```python
   if decision.action == "teach":
       output = await self.teaching_agent.run(... mode=decision.teach_mode ...)
       yield _sse("chunk", text=output.content)
       if output.mermaid_code:
           yield _sse("image_mermaid", code=output.mermaid_code)
       if output.questions:
           yield _sse("questions", items=output.questions)
       # 持久化：把 assistant 的 turn 加到 recent_turns（截断到最近 8 条）
       session.recent_turns = (session.recent_turns + [{"role":"assistant","content":output.content}])[-8:]
       new_state = "QUESTIONING" if output.questions else "QUESTIONING"  # probe_stuck 也是等用户回话
       update_session(db, session.id, state=new_state, recent_turns=session.recent_turns, ...)
       yield _sse("state_change", from_=session.state, to=new_state)
       session.state = new_state
   ```

6. **测试题生成（CONFIRMING_TEST → TESTING）**：
   - 由 `TeachingAgent` 在一个特殊 mode 中生成 3 题（new mode："generate_test"）—— 或者更简单：直接调 `chat_json` 一次性返回 `{"questions":[...]}`，存到 `session.test_questions`，然后 emit 第一题
   - 推荐做法：在 service.py 里直接写一个内联函数 `_generate_test_questions(node_name, what_list, weak_points) -> list[str]`，3 道题，prompt 直接内联在函数里（不必走 config 文件），返回 list

7. **mark_node_learned**：
   ```python
   db.execute("UPDATE nodes SET status='learned' WHERE id=?", (session.node_id,))
   db.commit()
   update_session(db, session.id, state="COMPLETED", status="completed", ended_at=NOW())
   yield _sse("node_completed", node_id=session.node_id)
   ```

8. **restart 命令**：
   ```python
   abandon_session(db, session.id)
   new_session = create_session(db, user_id=..., node_id=..., plan_id=..., what_list=session.what_list)
   yield _sse("restart", new_session_id=new_session.id)
   # 不在此响应里继续讲；前端收到 restart 后会用新 session_id 重新调 /initialize
   ```

9. **概念状态更新**：当 service 把某个 index 标 done/skipped，必须 yield 一条 `concept_update` 事件让前端更新左侧进度。

10. **每完成一次 SSE generator 末尾，把 session 的最新状态再写一次 DB（防止中途漏写）**。

**Verify**：写一个本地脚本走通"新建 session → /initialize → 用户答题 → /message → /command continue"的完整链路，打印所有 SSE 事件，对照 0.4 节验证。

---

### B-09：Router

**File**：`backend/routers/deep_learn.py`

**Goal**：把 service 的 4 个 API 暴露成 HTTP endpoint。

**Endpoints**（与 PRD §7 完全一致）：

```python
router = APIRouter(prefix="/api/deep-learn", tags=["DeepLearn"])
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

@router.post("/sessions")
async def create_session(
    req: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: DbSession = Depends(get_db),
) -> dict:
    # 1. 验证 plan 归属 user（防越权）
    # 2. 调 service.get_or_create_session
    # 3. 返回 {"success": True, "data": CreateSessionData(...).model_dump()}
    # is_resumed = (返回的 session.state != "INITIALIZING")
    ...

@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DbSession = Depends(get_db),
) -> dict:
    # 返回 {"success": True, "data": session.model_dump() + node_meta}
    ...

@router.post("/sessions/{session_id}/initialize")
async def initialize(
    session_id: str,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
):
    # SSE response; service 内部用 get_db_context 拿连接
    ...

@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    req: MessageRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
):
    ...

@router.post("/sessions/{session_id}/command")
async def send_command(
    session_id: str,
    req: CommandRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
):
    ...
```

**实现要点**：
- 三个 SSE endpoint **不要**用 `Depends(get_db)`（DI 的 db 会在 generator 返回前被关闭）。改用 `get_db_context()` 在 service 内部按需打开短连接
- 在 SSE generator 里循环检查 `await http_request.is_disconnected()`，断线立即 return
- session 权限检查：所有 endpoint 拿到 session 后**必须**验证 `session.user_id == user_id`，否则 raise 403

**Verify**：用 curl 跑：
```bash
curl -X POST .../api/deep-learn/sessions -H "Authorization: Bearer ..." -d '{"node_id":"...","plan_id":"..."}'
# 应返回 {"success": true, "data": {...session_id, ...}}
```

---

### B-10：注册 Router

**File**：`backend/main.py`

**修改 2 处**：

```python
# 第 19 行附近，新增 deep_learn import
from routers import ai, auth, deep_learn, graph, notes, plans, stats, user

# 第 113 行附近，include_router
app.include_router(ai.router)
app.include_router(deep_learn.router)   # ← 新增这一行
```

**Verify**：启动后端，访问 `/docs`（DEBUG 模式）应看到 `/api/deep-learn/...` 路径。

---

## Part 2 · Frontend Tasks

### F-01：API Client

**File**：`frontend/src/services/deepLearnApi.js`

**Goal**：封装所有 5 个后端 endpoint 调用；SSE 返回原始 `Response` 对象供 hook 消费。

```javascript
import { tokenManager } from './api';
import { buildApiUrl } from '../config/api';

const authHeaders = () => {
  const token = tokenManager.get();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const deepLearnApi = {
  createSession: async ({ nodeId, planId }) => {
    const res = await fetch(buildApiUrl('/api/deep-learn/sessions'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ node_id: nodeId, plan_id: planId }),
    });
    if (!res.ok) throw new Error(`createSession failed: ${res.status}`);
    return res.json();   // { success, data: {...} }
  },

  getSession: async (sessionId) => {
    const res = await fetch(buildApiUrl(`/api/deep-learn/sessions/${sessionId}`), {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`getSession failed: ${res.status}`);
    return res.json();
  },

  // 三个 SSE endpoint 返回 Response，由 hook 消费 body 流
  initialize: (sessionId) => fetch(
    buildApiUrl(`/api/deep-learn/sessions/${sessionId}/initialize`),
    { method: 'POST', headers: authHeaders() },
  ),

  sendMessage: (sessionId, content) => fetch(
    buildApiUrl(`/api/deep-learn/sessions/${sessionId}/message`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ content }),
    },
  ),

  sendCommand: (sessionId, command) => fetch(
    buildApiUrl(`/api/deep-learn/sessions/${sessionId}/command`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ command }),
    },
  ),
};
```

**Verify**：浏览器 console 直接调 `await deepLearnApi.createSession({...})` 应返回数据。

---

### F-02：useDeepLearnSession Hook（核心 · SSE 消费）

**File**：`frontend/src/hooks/useDeepLearnSession.js`

**Goal**：管理整个 page 的状态：session、messages、UI flags；消费 SSE 流；提供 `sendMessage`/`sendCommand` 接口。

**导出 hook 签名**：

```javascript
export function useDeepLearnSession({ planId, nodeId }) {
  return {
    session,              // { sessionId, state, nodeName, nodeWhy, whatList, ... }
    messages,             // [{ role: 'user'|'assistant', kind: 'text'|'mermaid'|'assessment', content }]
    conceptsStatus,       // { "0": "done", "1": "current", ... }
    weakPoints,           // string[]
    isStreaming,          // bool
    uiFlags: {
      showCommands: bool,           // 显示 [continue/expand/skip/reteach]
      showTestConfirm: object|null, // { message, commands: [...] }
      showFailOptions: object|null, // { message, options: [...] }
    },
    sendMessage,          // (text) => Promise<void>
    sendCommand,          // (cmd) => Promise<void>
    error,                // string|null
  };
}
```

**SSE 消费器实现**：

```javascript
async function consumeSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 2);
      if (block.startsWith('data:')) {
        try { onEvent(JSON.parse(block.slice(5).trim())); } catch (_) { /* skip */ }
      }
    }
  }
}
```

**事件 → state 映射**（与 0.4 节一一对应）：

| 事件类型 | hook 处理 |
|---------|----------|
| `chunk` | 追加到当前 assistant message 的 content；如无则新建一个 |
| `image_mermaid` | 新增一条 message `{role:'assistant', kind:'mermaid', content: event.code}` |
| `state_change` | 更新 `session.state`，重置 uiFlags（仅在新增其他 flag 时） |
| `concept_update` | `conceptsStatus[event.index] = event.status` |
| `questions` | 新增一条 message `{role:'assistant', kind:'questions', content: event.items}` |
| `assessment` | 新增一条 message `{role:'assistant', kind:'assessment', content: event}` |
| `show_commands` | `uiFlags.showCommands = true; showTestConfirm = showFailOptions = null` |
| `test_confirm_prompt` | `uiFlags.showTestConfirm = event` |
| `fail_options` | `uiFlags.showFailOptions = event` |
| `node_completed` | 弹一个 toast「节点已掌握 🎉」，跳转回 `/graph/:planId` 或停在此页 |
| `restart` | 用 `event.new_session_id` 替换 sessionId，messages 清空，再调一次 `initialize` |
| `error` | `setError(event.error.message)` |
| `done` | `isStreaming = false`；finalize 当前 assistant message |

**初始化逻辑**：

```javascript
useEffect(() => {
  let cancelled = false;
  (async () => {
    const res = await deepLearnApi.createSession({ nodeId, planId });
    if (cancelled) return;
    const data = res.data;
    setSession({ sessionId: data.session_id, state: data.state, nodeName: data.node_name, nodeWhy: data.node_why, whatList: data.what_list });
    setConceptsStatus(data.concepts_status);
    setWeakPoints(data.weak_points);

    if (data.state === 'INITIALIZING') {
      // 新 session，立即触发初始讲解
      await streamFrom(deepLearnApi.initialize(data.session_id));
    } else {
      // resume：回填 recent_turns 为 messages，根据 state 决定 uiFlags
      setMessages(data.recent_turns.map(t => ({ role: t.role, kind: 'text', content: t.content })));
      // 简单恢复策略：state 是 AWAITING_COMMAND 时 showCommands；CONFIRMING_TEST 时 showTestConfirm；CHOOSING_AFTER_FAIL 时 showFailOptions
      // Phase 1 可以更简单：恢复时只提示「已恢复进度，可继续输入或点击命令」，showCommands=true（让用户点 continue 触发下一步）
    }
  })();
  return () => { cancelled = true; };
}, [planId, nodeId]);
```

**Verify**：在 DeepLearnPage 里挂载 hook，console 打印每个事件，跑一遍流程无遗漏。

---

### F-03：App.jsx 路由

**修改**：`frontend/src/App.jsx`

```jsx
// import 区域新增
import DeepLearnPage from './pages/DeepLearnPage';

// <Routes> 内，在 /graph/:planId 路由之后新增
<Route
  path="/deep-learn/:planId/:nodeId"
  element={
    <ProtectedRoute>
      <DeepLearnPage />
    </ProtectedRoute>
  }
/>
```

---

### F-04：DeepLearnPage（Shell）

**File**：`frontend/src/pages/DeepLearnPage.jsx`

**Goal**：左右分栏 layout；header；挂载 hook；分发到子组件。

```jsx
export default function DeepLearnPage() {
  const { planId, nodeId } = useParams();
  const navigate = useNavigate();
  const {
    session, messages, conceptsStatus, weakPoints, isStreaming,
    uiFlags, sendMessage, sendCommand, error,
  } = useDeepLearnSession({ planId, nodeId });

  if (!session) return <FullScreenLoader text="正在准备学习环境..." />;

  return (
    <div className="flex flex-col h-screen bg-[#FAFAFA] overflow-hidden">
      <Header
        nodeName={session.nodeName}
        onBack={() => navigate(`/graph/${planId}`)}
        onRestart={() => sendCommand('restart')}
      />
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-72 shrink-0 border-r border-zinc-200 bg-white overflow-y-auto">
          <ConceptProgress
            whatList={session.whatList}
            conceptsStatus={conceptsStatus}
            weakPoints={weakPoints}
          />
        </aside>
        <main className="flex-1 overflow-hidden flex flex-col">
          {error && <ErrorBanner message={error} />}
          <DeepLearnChat
            messages={messages}
            isStreaming={isStreaming}
            uiFlags={uiFlags}
            onSendMessage={sendMessage}
            onSendCommand={sendCommand}
          />
        </main>
      </div>
    </div>
  );
}
```

**实现要点**：
- `Header`/`FullScreenLoader`/`ErrorBanner` 都内联实现，不要新建文件
- Header 用现有 `lucide-react` 图标（ArrowLeft、RotateCcw）

---

### F-05：ConceptProgress

**File**：`frontend/src/components/deep-learn/ConceptProgress.jsx`

**Props**：`{ whatList: string[], conceptsStatus: Record<string,string>, weakPoints: string[] }`

**实现要点**：
- 顶部：进度条（done / total）
- 中部：概念列表，每行：状态图标 + 文字
- 状态 → 图标映射：
  - `done` → `CheckCircle2`，绿色
  - `current` → `ChevronRight`，蓝色 + 浅蓝背景
  - `skipped` → `SkipForward`，灰色
  - `pending` → `Circle`，浅灰
- 底部：弱点列表（黄色 `AlertTriangle` 图标），仅 weakPoints.length > 0 时显示

---

### F-06：DeepLearnChat

**File**：`frontend/src/components/deep-learn/DeepLearnChat.jsx`

**Props**：`{ messages, isStreaming, uiFlags, onSendMessage, onSendCommand }`

**结构**：
1. **滚动消息区**（flex-1，overflow-y-auto）
   - 遍历 messages：根据 `kind` 分发：
     - `text` → 用户消息（右对齐黑底）/ AI 消息（左对齐 `ChatMarkdownMessage`）
     - `mermaid` → `<MermaidDiagram code={content} />`
     - `questions` → 一个圆角卡片，列出 3 道题
     - `assessment` → 圆角卡片，✅/❌ + explanation + feedback
   - 末尾 `<div ref={bottomRef} />` 用 `useEffect` 自动滚到底
2. **UI flag 区**（在消息区下方、输入框上方）
   - `uiFlags.showTestConfirm` → 蓝色卡片 + `<CommandBar commands={['confirm_test','not_ready']} />`
   - `uiFlags.showFailOptions` → 黄色卡片 + `<CommandBar commands={...} labels={...} />`
   - `uiFlags.showCommands && !其他 flag` → `<CommandBar commands={['continue','expand','skip','reteach']} />`
3. **输入框**
   - textarea + Send 按钮
   - 流式中 disabled
   - Enter 提交、Shift+Enter 换行

---

### F-07：CommandBar + MermaidDiagram

**File A**：`frontend/src/components/deep-learn/CommandBar.jsx`

```jsx
const LABELS = {
  continue: '继续 →',
  expand: '展开',
  skip: '跳过',
  reteach: '重讲',
  confirm_test: '✅ 开始测试',
  not_ready: '再复习一下',
  restart: '🔄 重新开始',
};

export default function CommandBar({ commands, labels = {}, onCommand }) {
  return (
    <div className="flex flex-wrap gap-2">
      {commands.map(cmd => (
        <button
          key={cmd}
          onClick={() => onCommand(cmd)}
          className="px-3 py-1.5 rounded-lg text-sm border border-zinc-200 bg-white hover:bg-zinc-50 transition-colors"
        >
          {labels[cmd] || LABELS[cmd] || cmd}
        </button>
      ))}
    </div>
  );
}
```

**File B**：`frontend/src/components/deep-learn/MermaidDiagram.jsx`

先安装：`npm install mermaid` （在 `frontend/` 目录）

```jsx
import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
let _uid = 0;

export default function MermaidDiagram({ code }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current || !code) return;
    const id = `mermaid-${++_uid}`;
    mermaid.render(id, code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => {
      if (ref.current) ref.current.textContent = '[图表渲染失败]';
    });
  }, [code]);
  return <div ref={ref} className="my-3 p-4 bg-zinc-50 rounded-xl border border-zinc-200 overflow-x-auto" />;
}
```

---

## Part 3 · Smoke Tests（手动验证）

每个场景必须能完整跑通，无 console error。

### T-01：新 session 完整 happy path

1. 在 GraphPage 选一个 `what` 列表非空的节点 → 跳转 `/deep-learn/:planId/:nodeId`
2. 期望：左侧显示概念列表（第一个是 current，其余 pending）
3. 右侧 AI 讲第一个概念 + 3 道题
4. 答对一题 → 看到 ✅ assessment + `[continue/expand/skip/reteach]` 按钮
5. 点 continue → 讲第二个概念
6. 重复直到所有概念 done
7. 自动进入 readiness check → AI 询问"准备好测试？"
8. 点 confirm_test → 测试题 1/3
9. 依次答完 3 题 → 通过 → toast 提示，节点 status 变 learned

### T-02：Resume

1. T-01 进行到第 5 步时关闭浏览器标签
2. 重新打开同一节点的深入学习页面
3. 期望：左侧概念进度保留，右侧消息显示"已恢复进度..."（或最近对话）
4. 点 continue 能继续

### T-03：Skip 概念

1. 在 AWAITING_COMMAND 状态点 skip
2. 期望：左侧该概念变 `skipped`（灰色 SkipForward 图标），跳到下一概念

### T-04：连续两次答错触发 probe_stuck

1. 故意对同一概念的题答错 2 次
2. 期望：第 2 次评估后 AI 不再给答案，只问澄清问题（没有 questions 卡片，没有 `show_commands`）

### T-05：测试未通过

1. 测试题全部胡乱回答
2. 综合判定 passed=false
3. 期望：黄色卡片显示 [🔄 重新开始 / 📚 针对弱点复习] 两个按钮
4. 点 restart → 旧 session 标 abandoned，新 session 创建并自动开始
5. 点 not_ready → AI 进入 review_weak 模式补讲

---

## Part 4 · Anti-patterns（禁止）

| 反模式 | 正确做法 |
|--------|---------|
| 在 Python 里写 `CREATE TABLE` 或调用 migration 工具 | DDL 一律在 Supabase SQL Editor 手动执行 |
| 读 JSONB 字段后再 `json.loads` | psycopg2 RealDictCursor 已自动反序列化 |
| 在 SSE generator 内部用 FastAPI `Depends(get_db)` | 用 `with get_db_context() as db:` 显式短连接 |
| 在 state machine 文件里 import 任何 DB/LLM 模块 | state machine 是纯函数 |
| 在 LLM 输出里允许 Markdown 代码块包装 JSON | prompt 中明确要求纯 JSON；解析失败兜底返回 fallback object |
| 在前端用 EventSource | EventSource 不支持自定义 Header（无法带 JWT）。必须用 `fetch` + 手动解析 SSE 流 |
| 在 hook 里把 messages 用 ref 存 + setState 双轨 | 只用一份 state；用函数式 `setMessages(prev => ...)` 避免闭包陈旧 |
| 用 `process.env` 访问环境变量（Vite 项目） | 用 `import.meta.env.VITE_*` |
| concepts_status 用概念字符串做 key | 必须用 index 字符串（"0"/"1"/...）|
| 把所有事件类型在 hook 用 dict-dispatch | 用 switch/if-elif，便于断点调试 |
| 在节点详情页直接 import DeepLearnPage 实现"内嵌"工作台 | 工作台是独立 route，跳页打开 |

---

## 执行顺序建议

**第 1 天**：B-01（5 分钟）→ B-02 → B-03 → B-04 + 单元测试
**第 2 天**：B-05 → B-06 → B-07
**第 3 天**：B-08 → B-09 → B-10，curl 跑通 T-01 后端流
**第 4 天**：F-01 → F-02 → F-03 → F-04
**第 5 天**：F-05 → F-06 → F-07
**第 6 天**：T-01 ~ T-05 端到端验证 + fix bug

每完成一个 Task 必须用对应 `Verify` 步骤验证后再进入下一个。

---

## 完成定义（Phase 1 Done）

- [ ] B-04 单元测试全部通过
- [ ] T-01 ~ T-05 五个 smoke test 全部手动验证通过
- [ ] 浏览器 console 在完整 happy path 中无 error 或 warning
- [ ] `nodes.status` 在测试通过后正确变更为 `learned`
- [ ] 节点详情页加上"深入学习"按钮（GraphPage 集成，1 行代码）
