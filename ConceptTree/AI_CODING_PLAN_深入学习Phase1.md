# AI Coding Plan: 深入学习工作台 Phase 1

> 供 AI coding agent 直接执行。每个 Task 独立可验证，按依赖顺序实施。

---

## 环境约束（必读）

- **数据库**：PostgreSQL via psycopg2，Supabase 管理迁移。**禁止调用 `init_database()`**，新表通过 SQL 迁移文件创建。
- **占位符**：SQL 用 `?`，`database.py` 内部自动转 `%s`。JSON 字段用 `psycopg2.extras.Json` 包装（`_adapt_params` 已处理）。
- **DB 访问**：FastAPI DI 用 `get_db`；后台任务用 `get_db_context()`。
- **认证**：`from utils.auth import get_current_user_id`（FastAPI Depends）。
- **LLM**：`from services.llm import get_llm_client`，方法 `chat_json()` 和 `chat_stream()`。
- **SSE 模式**：参考 `routers/ai.py` 的 `StreamingResponse` + async generator。
- **错误响应格式**：`{"success": false, "error": {"code": "XX", "message": "xx"}}`。
- **前端技术栈**：React + React Router + Tailwind CSS，已有 `ChatMarkdownMessage`、`MarkdownContent` 组件可复用。

---

## 依赖关系图

```
Task 1 (DB Migration)
  └── Task 3 (Session Repo)
        └── Task 4 (Orchestrator)
              └── Task 7 (Service)
                    ├── Task 8 (Router)
                    │     └── Task 9 (main.py 注册)
                    └── Task 5 (Teaching Agent)  ─┐
Task 2 (Models) ─────────────────────────────────┤→ Task 7
                                  Task 6 (Assessment Agent) ─┘

Task 10 (Frontend API)
  └── Task 17 (SSE Hook)
        └── Task 12 (DeepLearnPage)
              ├── Task 13 (ConceptProgress)
              ├── Task 14 (DeepLearnChat)
              │     ├── Task 15 (CommandBar)
              │     └── Task 16 (MermaidDiagram)
              └── Task 11 (App.jsx Route) [可并行]
```

---

## Task 1 — 数据库迁移

**文件**：`backend/scripts/migration_deep_learn_sessions.sql`

```sql
-- deep_learn_sessions: 学习 session 状态持久化
CREATE TABLE IF NOT EXISTS deep_learn_sessions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL,
    node_id               TEXT NOT NULL,
    plan_id               TEXT NOT NULL,
    state                 TEXT NOT NULL DEFAULT 'INITIALIZING',
    current_concept_index INTEGER NOT NULL DEFAULT 0,
    difficulty_level      INTEGER NOT NULL DEFAULT 3,
    wrong_count_current   INTEGER NOT NULL DEFAULT 0,
    concepts_status       JSONB NOT NULL DEFAULT '{}',
    weak_points           JSONB NOT NULL DEFAULT '[]',
    recent_turns          JSONB NOT NULL DEFAULT '[]',
    what_list             JSONB NOT NULL DEFAULT '[]',
    conversation_summary  TEXT,
    started_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at              TIMESTAMPTZ,
    status                TEXT NOT NULL DEFAULT 'in_progress',
    CONSTRAINT dl_sessions_state_check CHECK (state IN (
        'INITIALIZING','PROBING','TEACHING','QUESTIONING','EVALUATING',
        'AWAITING_COMMAND','AI_ASSESSING_READINESS','CONFIRMING_TEST',
        'TESTING','EVALUATING_TEST','CHOOSING_AFTER_FAIL',
        'GENERATING_NOTE','COMPLETED'
    )),
    CONSTRAINT dl_sessions_status_check CHECK (
        status IN ('in_progress','completed','abandoned')
    )
);

CREATE INDEX IF NOT EXISTS idx_dl_sessions_user_node_status
    ON deep_learn_sessions(user_id, node_id, status);

-- learning_session_records: session 结束后写入的 episodic memory
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
```

**执行方式**：在 Supabase SQL Editor 执行此文件。不要在 Python 里调用。

**验收**：两张表存在，`deep_learn_sessions` 能插入一行并查询 `id`。

---

## Task 2 — Pydantic Models

**文件**：`backend/models_deep_learn.py`

```python
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DeepLearnState(str, Enum):
    INITIALIZING           = "INITIALIZING"
    PROBING                = "PROBING"
    TEACHING               = "TEACHING"
    QUESTIONING            = "QUESTIONING"
    EVALUATING             = "EVALUATING"
    AWAITING_COMMAND       = "AWAITING_COMMAND"
    AI_ASSESSING_READINESS = "AI_ASSESSING_READINESS"
    CONFIRMING_TEST        = "CONFIRMING_TEST"
    TESTING                = "TESTING"
    EVALUATING_TEST        = "EVALUATING_TEST"
    CHOOSING_AFTER_FAIL    = "CHOOSING_AFTER_FAIL"
    GENERATING_NOTE        = "GENERATING_NOTE"
    COMPLETED              = "COMPLETED"


class DeepLearnCommand(str, Enum):
    CONTINUE     = "continue"       # 继续下一概念
    EXPAND       = "expand"         # 展开当前概念
    SKIP         = "skip"           # 跳过当前概念
    RETEACH      = "reteach"        # 重讲当前概念
    RESTART      = "restart"        # 重新开始整个 session
    CONFIRM_TEST = "confirm_test"   # 确认进入综合测试
    NOT_READY    = "not_ready"      # 还没准备好，继续学


class ConceptStatus(str, Enum):
    PENDING  = "pending"
    CURRENT  = "current"
    DONE     = "done"
    SKIPPED  = "skipped"


class ConceptItem(BaseModel):
    text: str
    status: ConceptStatus = ConceptStatus.PENDING


class Turn(BaseModel):
    role: str    # "assistant" | "user"
    content: str


class SessionState(BaseModel):
    """完整的 session 状态，对应 deep_learn_sessions 表一行"""
    id: str
    user_id: str
    node_id: str
    plan_id: str
    state: DeepLearnState
    current_concept_index: int
    difficulty_level: int                 # 1-5
    wrong_count_current: int
    concepts_status: Dict[str, str]       # concept_text -> ConceptStatus value
    weak_points: List[str]
    recent_turns: List[Dict[str, str]]    # [{role, content}]
    what_list: List[str]
    conversation_summary: Optional[str]
    status: str


# ── API Request / Response models ──────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    node_id: str
    plan_id: str

class CreateSessionResponse(BaseModel):
    success: bool
    session_id: str
    state: str
    is_resumed: bool
    what_list: List[str]
    concepts_status: Dict[str, str]

class MessageRequest(BaseModel):
    content: str

class CommandRequest(BaseModel):
    command: DeepLearnCommand

class SessionStateResponse(BaseModel):
    success: bool
    data: Dict[str, Any]

# ── Agent output models (internal, for JSON parsing) ────────────────────────

class TeachingAgentOutput(BaseModel):
    content: str
    questions: List[str] = Field(default_factory=list)
    needs_image: bool = False
    image_type: Optional[str] = None   # "mermaid" | "dalle"
    mermaid_code: Optional[str] = None

class AssessmentAgentOutput(BaseModel):
    is_correct: bool
    quality_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    feedback: str
    update_weak_points: List[str] = Field(default_factory=list)
    difficulty_delta: int = 0          # -1 | 0 | 1
    wrong_count: int = 0

class ReadinessAgentOutput(BaseModel):
    ready_for_test: bool
    reasoning: str
    suggest_review_concepts: List[str] = Field(default_factory=list)
```

**验收**：`from models_deep_learn import DeepLearnState, SessionState` 不报错。

---

## Task 3 — Session Repository

**文件**：`backend/services/deep_learn/session_repo.py`

实现以下函数，全部接收 `DbSession`，返回 `Optional[SessionState]` 或 `str`（id）：

```python
from __future__ import annotations
import json
from typing import Optional
from database import DbSession
from models_deep_learn import SessionState, DeepLearnState


def get_active_session(db: DbSession, user_id: str, node_id: str) -> Optional[SessionState]:
    """查找该用户该节点最近一条 in_progress session，用于断点续学"""
    row = db.execute(
        """SELECT * FROM deep_learn_sessions
           WHERE user_id = ? AND node_id = ? AND status = 'in_progress'
           ORDER BY updated_at DESC LIMIT 1""",
        (user_id, node_id),
    ).fetchone()
    return _row_to_state(row) if row else None


def create_session(
    db: DbSession,
    user_id: str,
    node_id: str,
    plan_id: str,
    what_list: list[str],
) -> SessionState:
    """新建 session，初始状态 INITIALIZING"""
    concepts_status = {c: "pending" for c in what_list}
    row = db.execute(
        """INSERT INTO deep_learn_sessions
           (user_id, node_id, plan_id, state, what_list, concepts_status)
           VALUES (?, ?, ?, 'INITIALIZING', ?, ?)
           RETURNING *""",
        (user_id, node_id, plan_id, what_list, concepts_status),
    ).fetchone()
    db.commit()
    return _row_to_state(row)


def update_session(db: DbSession, session_id: str, **fields) -> None:
    """
    更新任意字段。支持的 fields：
    state, current_concept_index, difficulty_level, wrong_count_current,
    concepts_status, weak_points, recent_turns, conversation_summary,
    status, ended_at
    """
    allowed = {
        "state", "current_concept_index", "difficulty_level",
        "wrong_count_current", "concepts_status", "weak_points",
        "recent_turns", "conversation_summary", "status", "ended_at",
    }
    filtered = {k: v for k, v in fields.items() if k in allowed}
    if not filtered:
        return
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    set_clause += ", updated_at = NOW()"
    db.execute(
        f"UPDATE deep_learn_sessions SET {set_clause} WHERE id = ?",
        list(filtered.values()) + [session_id],
    )
    db.commit()


def get_session_by_id(db: DbSession, session_id: str, user_id: str) -> Optional[SessionState]:
    row = db.execute(
        "SELECT * FROM deep_learn_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    return _row_to_state(row) if row else None


def _row_to_state(row) -> SessionState:
    def load(v):
        return json.loads(v) if isinstance(v, str) else (v or {})

    return SessionState(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        node_id=row["node_id"],
        plan_id=row["plan_id"],
        state=DeepLearnState(row["state"]),
        current_concept_index=row["current_concept_index"],
        difficulty_level=row["difficulty_level"],
        wrong_count_current=row["wrong_count_current"],
        concepts_status=load(row["concepts_status"]),
        weak_points=load(row["weak_points"]) if isinstance(row["weak_points"], (str, list)) else [],
        recent_turns=load(row["recent_turns"]) if isinstance(row["recent_turns"], (str, list)) else [],
        what_list=load(row["what_list"]) if isinstance(row["what_list"], (str, list)) else [],
        conversation_summary=row.get("conversation_summary"),
        status=row["status"],
    )
```

**验收**：`create_session` 成功插入并返回 `SessionState`；`get_active_session` 能查到刚插入的记录。

---

## Task 4 — 状态机 Orchestrator

**文件**：`backend/services/deep_learn/orchestrator.py`

状态机是**纯代码逻辑**，不调用 LLM。它接收当前 state + 事件，返回下一个 state 和副作用指令。

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from models_deep_learn import DeepLearnState, DeepLearnCommand, ConceptStatus


@dataclass
class TransitionResult:
    next_state: DeepLearnState
    action: str           # 告诉 Service 层该做什么
    # action 枚举值：
    # "run_teaching"        → 调用 Teaching Agent 讲当前概念
    # "run_assessment"      → 调用 Assessment Agent 评估用户回答
    # "run_readiness_check" → 调用 Assessment Agent 判断是否准备好
    # "run_test_question"   → 调用 Teaching Agent 生成综合测试题
    # "run_test_evaluation" → 调用 Assessment Agent 综合判定测试
    # "show_command_prompt" → 前端显示控制按钮，等待指令
    # "show_test_confirm"   → 询问用户是否准备好测试
    # "show_fail_options"   → 展示失败选项（重来/复习弱点）
    # "noop"                → 无操作（等待用户输入）
    meta: Optional[dict] = None


class SessionOrchestrator:

    def on_session_created(self) -> TransitionResult:
        """新 session 创建后，初始动作"""
        return TransitionResult(
            next_state=DeepLearnState.PROBING,
            action="run_teaching",   # 用第一个概念探测难度
        )

    def on_user_message(
        self,
        current_state: DeepLearnState,
        wrong_count: int,
        all_concepts_done: bool,
    ) -> TransitionResult:
        """用户发送了一条普通消息（非命令）"""

        if current_state == DeepLearnState.PROBING:
            # 探测题收到回答 → 评估，校准难度
            return TransitionResult(
                next_state=DeepLearnState.EVALUATING,
                action="run_assessment",
            )

        if current_state == DeepLearnState.QUESTIONING:
            # 用户回答了题目 → 评估
            return TransitionResult(
                next_state=DeepLearnState.EVALUATING,
                action="run_assessment",
            )

        if current_state == DeepLearnState.TESTING:
            return TransitionResult(
                next_state=DeepLearnState.EVALUATING_TEST,
                action="run_test_evaluation",
            )

        if current_state in (DeepLearnState.AWAITING_COMMAND, DeepLearnState.CONFIRMING_TEST):
            # 用户没用按钮，直接输入文字 → 当作普通消息，run_teaching 处理
            if all_concepts_done:
                return TransitionResult(
                    next_state=DeepLearnState.AI_ASSESSING_READINESS,
                    action="run_readiness_check",
                )
            return TransitionResult(
                next_state=DeepLearnState.TEACHING,
                action="run_teaching",
            )

        return TransitionResult(next_state=current_state, action="noop")

    def on_assessment_done(
        self,
        current_state: DeepLearnState,
        is_correct: bool,
        wrong_count: int,
        all_concepts_done: bool,
    ) -> TransitionResult:
        """Assessment Agent 评估完毕后"""

        if wrong_count >= 2:
            # 连续两次答错：不再给答案，用 TEACHING 状态但 action 是追问
            return TransitionResult(
                next_state=DeepLearnState.QUESTIONING,
                action="run_teaching",
                meta={"mode": "probe_stuck"},
            )

        if current_state == DeepLearnState.EVALUATING_TEST:
            if is_correct:
                return TransitionResult(
                    next_state=DeepLearnState.COMPLETED,
                    action="run_teaching",   # 输出通过提示
                    meta={"mode": "test_passed"},
                )
            else:
                return TransitionResult(
                    next_state=DeepLearnState.CHOOSING_AFTER_FAIL,
                    action="show_fail_options",
                )

        # 普通概念评估后 → 进入 AWAITING_COMMAND
        return TransitionResult(
            next_state=DeepLearnState.AWAITING_COMMAND,
            action="show_command_prompt",
        )

    def on_command(
        self,
        command: DeepLearnCommand,
        current_concept_index: int,
        what_list_len: int,
    ) -> TransitionResult:
        """用户发送了控制命令"""

        next_idx = current_concept_index + 1
        has_more = next_idx < what_list_len

        if command == DeepLearnCommand.CONTINUE:
            if has_more:
                return TransitionResult(
                    next_state=DeepLearnState.TEACHING,
                    action="run_teaching",
                    meta={"advance_index": True},
                )
            else:
                return TransitionResult(
                    next_state=DeepLearnState.AI_ASSESSING_READINESS,
                    action="run_readiness_check",
                )

        if command == DeepLearnCommand.EXPAND:
            return TransitionResult(
                next_state=DeepLearnState.TEACHING,
                action="run_teaching",
                meta={"mode": "expand"},
            )

        if command == DeepLearnCommand.SKIP:
            meta = {"mark_skipped": True}
            if has_more:
                meta["advance_index"] = True
                return TransitionResult(
                    next_state=DeepLearnState.TEACHING,
                    action="run_teaching",
                    meta=meta,
                )
            else:
                return TransitionResult(
                    next_state=DeepLearnState.AI_ASSESSING_READINESS,
                    action="run_readiness_check",
                    meta=meta,
                )

        if command == DeepLearnCommand.RETEACH:
            return TransitionResult(
                next_state=DeepLearnState.TEACHING,
                action="run_teaching",
                meta={"mode": "reteach"},
            )

        if command == DeepLearnCommand.RESTART:
            return TransitionResult(
                next_state=DeepLearnState.INITIALIZING,
                action="restart_session",
            )

        if command == DeepLearnCommand.CONFIRM_TEST:
            return TransitionResult(
                next_state=DeepLearnState.TESTING,
                action="run_test_question",
            )

        if command == DeepLearnCommand.NOT_READY:
            return TransitionResult(
                next_state=DeepLearnState.TEACHING,
                action="run_teaching",
                meta={"mode": "review_weak"},
            )

        return TransitionResult(next_state=DeepLearnState.AWAITING_COMMAND, action="noop")

    def on_readiness_checked(self, ready: bool) -> TransitionResult:
        if ready:
            return TransitionResult(
                next_state=DeepLearnState.CONFIRMING_TEST,
                action="show_test_confirm",
            )
        else:
            return TransitionResult(
                next_state=DeepLearnState.TEACHING,
                action="run_teaching",
                meta={"mode": "review_weak"},
            )
```

**验收**：给定任意 state + 事件输入，函数返回正确的 `next_state` 和 `action`（对照 PRD 状态转换表逐一测试）。

---

## Task 5 — Teaching Agent + Config

**文件 A**：`backend/services/llm/configs/deep_learn_teaching.json`

```json
{
  "model_params": {
    "temperature": 0.6,
    "max_tokens": 2048
  },
  "system_prompt": "你是一位专业的 1v1 AI 家教，严格遵守以下教学原则。\n\n[原则一：工作记忆保护]\n每次只讲一个概念。若该概念包含超过 3 个子概念，先给 2-3 句 overview，再逐个展开，每组不超过 3 个。每多写一句前问自己：「去掉它，理解会受损吗？」不会则删。\n\n[原则二：认知锚定（先激活，再挂载）]\n讲任何概念前，先一句话说清楚「它在做什么 / 为什么需要它」，再给 formal 定义。每个新概念出现时，先说它和前面讲过的是什么关系（依赖/对比/推广/特例）。非基础术语第一次出现时一句话定义，之后直接用。\n\n[原则三：逻辑连续性（无断链）]\n每段第一句是结论，后面跟推导或论据。每句话写完，下一句必须回答上一句引发的问号。段落内句子之间必须有因果/推演关系，禁止突然引入新内容。\n\n[原则四：不主动延伸]\n讲完一个知识点就停，不主动引入未讲过的新内容。可以往回指已学内容（retrieval cue），禁止往前扩未学内容。\n\n[输出格式]\n必须返回合法 JSON，不含任何 markdown 代码块包装：\n{\n  \"content\": \"讲解内容（Markdown 格式，中文）\",\n  \"questions\": [\"概念理解题\", \"应用/计算题\", \"误区陷阱题\"],\n  \"needs_image\": false,\n  \"image_type\": null,\n  \"mermaid_code\": null\n}"
}
```

**文件 B**：`backend/services/deep_learn/teaching_agent.py`

```python
from __future__ import annotations
import json
from typing import Optional
from services.llm import get_llm_client
from services.llm.providers import LLMMessage
from models_deep_learn import TeachingAgentOutput, SessionState


class TeachingAgent:
    def __init__(self):
        self.client = get_llm_client()
        self._load_config()

    def _load_config(self):
        import pathlib
        config_path = pathlib.Path(__file__).parent.parent / "llm/configs/deep_learn_teaching.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self._params = cfg.get("model_params", {})
        self._system_prompt = cfg.get("system_prompt", "")

    async def teach(
        self,
        session: SessionState,
        node_name: str,
        node_why: str,
        memory_context: str,
        mode: str = "normal",   # "normal" | "expand" | "reteach" | "probe_stuck" | "review_weak"
    ) -> TeachingAgentOutput:
        concept = session.what_list[session.current_concept_index]
        idx = session.current_concept_index
        total = len(session.what_list)
        difficulty = session.difficulty_level
        weak = ", ".join(session.weak_points) if session.weak_points else "无"

        mode_instructions = {
            "normal":      "按标准节奏讲解当前概念，然后出题。",
            "expand":      "对当前概念进行更深入展开，补充细节和边界情况，然后出更深的题。",
            "reteach":     "换一个全新的角度或类比重新讲解当前概念，不要重复之前的表述。",
            "probe_stuck": "用户连续答错，不要继续给答案。先问「你对哪一步感到困惑？」，等待回答后再针对性讲解。",
            "review_weak": f"用户感觉还没准备好，重点复习以下弱点：{weak}。",
        }

        user_prompt = (
            f"[节点] {node_name}\n"
            f"[学习目的] {node_why}\n"
            f"[当前概念] {concept}（第 {idx + 1} 个，共 {total} 个）\n"
            f"[当前难度级别] {difficulty}/5\n"
            f"[已识别弱点] {weak}\n"
            f"[记忆上下文]\n{memory_context}\n\n"
            f"[指令] {mode_instructions.get(mode, mode_instructions['normal'])}"
        )

        result = await self.client.chat_json(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=self._params.get("temperature", 0.6),
            max_tokens=self._params.get("max_tokens", 2048),
        )
        return TeachingAgentOutput(**result)
```

**验收**：调用 `teach()` 返回 `TeachingAgentOutput`，`content` 非空，`questions` 有 2-3 条。

---

## Task 6 — Assessment Agent + Config

**文件 A**：`backend/services/llm/configs/deep_learn_assessment.json`

```json
{
  "model_params": {
    "temperature": 0.3,
    "max_tokens": 1024
  },
  "system_prompt": "你是学习评估专家。根据用户对问题的回答，给出准确的质量评估。\n\n[评估标准]\n通过信号：\n- 能用自己的话正确解释核心概念（不是机械复述）\n- 能识别常见误区并说明为什么错\n- 对应用场景的判断基本正确\n\n不通过信号：\n- 机械复述原话，无法用例子说明\n- 对核心概念存在明显混淆且经提示后仍未纠正\n- 关键步骤答错且无法从 feedback 中修正\n\n边界情况：\n- 有小错误但整体心智模型正确 → is_correct=true，quality_score 给 0.7\n- quality_score < 0.6 时 → 追问，不要强行判定\n\n[输出格式]\n必须返回合法 JSON，不含任何 markdown 代码块包装：\n{\n  \"is_correct\": true,\n  \"quality_score\": 0.85,\n  \"explanation\": \"给用户看的一句话评价（中文，鼓励性）\",\n  \"feedback\": \"具体指出哪里对哪里有偏差（中文）\",\n  \"update_weak_points\": [],\n  \"difficulty_delta\": 0,\n  \"wrong_count\": 0\n}"
}
```

**文件 B**：`backend/services/deep_learn/assessment_agent.py`

```python
from __future__ import annotations
import json
import pathlib
from services.llm import get_llm_client
from models_deep_learn import AssessmentAgentOutput, ReadinessAgentOutput, SessionState


class AssessmentAgent:
    def __init__(self):
        self.client = get_llm_client()
        self._load_config()

    def _load_config(self):
        config_path = pathlib.Path(__file__).parent.parent / "llm/configs/deep_learn_assessment.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self._params = cfg.get("model_params", {})
        self._system_prompt = cfg.get("system_prompt", "")

    async def evaluate_answer(
        self,
        session: SessionState,
        question: str,
        user_answer: str,
        concept: str,
    ) -> AssessmentAgentOutput:
        user_prompt = (
            f"[概念] {concept}\n"
            f"[题目] {question}\n"
            f"[用户回答] {user_answer}\n"
            f"[当前弱点] {session.weak_points}\n"
            f"[连续错误次数] {session.wrong_count_current}"
        )
        result = await self.client.chat_json(
            system_prompt=self._system_prompt,
            user_prompt=user_prompt,
            temperature=self._params.get("temperature", 0.3),
            max_tokens=self._params.get("max_tokens", 1024),
        )
        return AssessmentAgentOutput(**result)

    async def check_readiness(self, session: SessionState, node_name: str) -> ReadinessAgentOutput:
        covered = [c for c, s in session.concepts_status.items() if s == "done"]
        skipped = [c for c, s in session.concepts_status.items() if s == "skipped"]
        system = (
            "你是一位严格的学习评估专家。根据学生的学习情况，判断他是否准备好进行综合测试。\n"
            "综合考虑：已覆盖概念数量、弱点列表、是否有大量跳过。\n"
            "如果弱点较多或有超过 30% 概念被跳过，建议先复习。\n"
            "输出合法 JSON：{\"ready_for_test\": bool, \"reasoning\": \"一句话理由\", \"suggest_review_concepts\": []}"
        )
        user_prompt = (
            f"[节点] {node_name}\n"
            f"[已学概念] {covered}\n"
            f"[跳过概念] {skipped}\n"
            f"[当前弱点] {session.weak_points}"
        )
        result = await self.client.chat_json(
            system_prompt=system,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=512,
        )
        return ReadinessAgentOutput(**result)
```

**验收**：`evaluate_answer()` 返回 `AssessmentAgentOutput`，`is_correct` 和 `quality_score` 字段存在。

---

## Task 7 — Deep Learn Service

**文件**：`backend/services/deep_learn/service.py`

这是核心协调层，把 Orchestrator + Agents + DB 串起来，**对外暴露两个主方法**：

```python
from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator, Optional
from database import get_db_context
from models_deep_learn import (
    DeepLearnCommand, DeepLearnState, SessionState, TeachingAgentOutput
)
from services.deep_learn.orchestrator import SessionOrchestrator
from services.deep_learn.session_repo import (
    create_session, get_active_session, get_session_by_id, update_session
)
from services.deep_learn.teaching_agent import TeachingAgent
from services.deep_learn.assessment_agent import AssessmentAgent

_CHECKPOINT_EVERY = 3   # 每 3 轮写一次 recent_turns


def _build_memory_context(session: SessionState) -> str:
    """构建注入 LLM 的记忆摘要（Phase 1 只用 short-term）"""
    lines = []
    if session.weak_points:
        lines.append(f"本次已识别弱点：{', '.join(session.weak_points)}")
    if session.conversation_summary:
        lines.append(f"对话摘要：{session.conversation_summary}")
    return "\n".join(lines) if lines else "暂无历史记忆。"


def _get_current_concept(session: SessionState) -> str:
    idx = session.current_concept_index
    if idx < len(session.what_list):
        return session.what_list[idx]
    return ""


def _all_concepts_done(session: SessionState) -> bool:
    return all(
        v in ("done", "skipped")
        for v in session.concepts_status.values()
    )


class DeepLearnService:
    def __init__(self):
        self.orchestrator = SessionOrchestrator()
        self.teaching_agent = TeachingAgent()
        self.assessment_agent = AssessmentAgent()

    async def get_or_create_session(
        self,
        user_id: str,
        node_id: str,
        plan_id: str,
    ) -> tuple[SessionState, bool]:
        """返回 (session, is_resumed)"""
        with get_db_context() as db:
            existing = get_active_session(db, user_id, node_id)
            if existing:
                return existing, True

            # 从 nodes 表读取 what_list
            row = db.execute(
                "SELECT what FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()
            what_list = []
            if row and row["what"]:
                raw = row["what"]
                what_list = json.loads(raw) if isinstance(raw, str) else raw

            session = create_session(db, user_id, node_id, plan_id, what_list)
            return session, False

    async def stream_initial(
        self, session: SessionState, node_name: str, node_why: str
    ) -> AsyncGenerator[str, None]:
        """新 session 的初始化流：探测难度，讲第一个概念"""
        result = self.orchestrator.on_session_created()
        yield _sse("state_change", {"from": session.state, "to": result.next_state})

        output = await self.teaching_agent.teach(
            session=session,
            node_name=node_name,
            node_why=node_why,
            memory_context=_build_memory_context(session),
            mode="normal",
        )
        async for event in self._stream_teaching_output(session, output, result.next_state):
            yield event

    async def stream_message(
        self,
        session: SessionState,
        user_message: str,
        node_name: str,
        node_why: str,
    ) -> AsyncGenerator[str, None]:
        """处理用户普通消息"""
        # 更新 recent_turns
        turns = list(session.recent_turns)
        turns.append({"role": "user", "content": user_message})
        session.recent_turns = turns[-8:]  # 保留最近 8 轮

        result = self.orchestrator.on_user_message(
            current_state=session.state,
            wrong_count=session.wrong_count_current,
            all_concepts_done=_all_concepts_done(session),
        )
        yield _sse("state_change", {"from": session.state, "to": result.next_state})

        if result.action == "run_assessment":
            async for event in self._handle_assessment(session, user_message, node_name, node_why):
                yield event
        elif result.action == "run_teaching":
            mode = (result.meta or {}).get("mode", "normal")
            output = await self.teaching_agent.teach(session, node_name, node_why, _build_memory_context(session), mode)
            async for event in self._stream_teaching_output(session, output, result.next_state):
                yield event
        elif result.action == "run_readiness_check":
            async for event in self._handle_readiness(session, node_name):
                yield event
        elif result.action == "run_test_evaluation":
            async for event in self._handle_test_evaluation(session, user_message, node_name):
                yield event

        await self._maybe_checkpoint(session)
        yield _sse("done", {})

    async def stream_command(
        self,
        session: SessionState,
        command: DeepLearnCommand,
        node_name: str,
        node_why: str,
    ) -> AsyncGenerator[str, None]:
        """处理控制命令"""
        result = self.orchestrator.on_command(
            command=command,
            current_concept_index=session.current_concept_index,
            what_list_len=len(session.what_list),
        )
        yield _sse("state_change", {"from": session.state, "to": result.next_state})
        meta = result.meta or {}

        # 处理副作用
        if meta.get("mark_skipped"):
            concept = _get_current_concept(session)
            session.concepts_status[concept] = "skipped"

        if meta.get("advance_index"):
            session.current_concept_index += 1

        if result.action == "restart_session":
            with get_db_context() as db:
                update_session(db, session.id, status="abandoned")
            yield _sse("restart", {})
            yield _sse("done", {})
            return

        if result.action in ("run_teaching",):
            mode = meta.get("mode", "normal")
            output = await self.teaching_agent.teach(session, node_name, node_why, _build_memory_context(session), mode)
            async for event in self._stream_teaching_output(session, output, result.next_state):
                yield event

        elif result.action == "run_readiness_check":
            async for event in self._handle_readiness(session, node_name):
                yield event

        elif result.action == "show_test_confirm":
            yield _sse("test_confirm_prompt", {"message": "好的，综合测试开始！我会出几道题考察你对本节点的整体掌握情况。准备好了告诉我。"})

        elif result.action == "run_test_question":
            output = await self.teaching_agent.teach(session, node_name, node_why, _build_memory_context(session), "normal")
            yield _sse("chunk", {"text": f"**综合测试题**\n\n{output.questions[0] if output.questions else '请综合回顾本节点所有内容，阐述你的理解。'}"})

        elif result.action == "show_fail_options":
            yield _sse("fail_options", {
                "message": "这次测试还没完全通过，你有两个选择：",
                "options": [
                    {"command": "restart", "label": "🔄 从头开始"},
                    {"command": "not_ready", "label": "📚 针对弱点复习"},
                ]
            })

        # 持久化 session 状态变化
        with get_db_context() as db:
            update_session(
                db, session.id,
                state=result.next_state,
                current_concept_index=session.current_concept_index,
                concepts_status=session.concepts_status,
            )

        await self._maybe_checkpoint(session)
        yield _sse("done", {})

    # ── 内部方法 ────────────────────────────────────────────────────────────

    async def _stream_teaching_output(
        self, session: SessionState, output: TeachingAgentOutput, next_state: DeepLearnState
    ) -> AsyncGenerator[str, None]:
        yield _sse("chunk", {"text": output.content})
        await asyncio.sleep(0)

        if output.needs_image and output.image_type == "mermaid" and output.mermaid_code:
            yield _sse("image_mermaid", {"code": output.mermaid_code})

        if output.questions:
            questions_text = "\n\n".join(f"**题 {i+1}**：{q}" for i, q in enumerate(output.questions))
            yield _sse("chunk", {"text": f"\n\n---\n\n{questions_text}"})
            yield _sse("questions", {"items": output.questions})
            next_state_after = DeepLearnState.QUESTIONING
        else:
            next_state_after = DeepLearnState.AWAITING_COMMAND

        # 更新概念状态
        concept = _get_current_concept(session)
        if concept:
            session.concepts_status[concept] = "current"

        with get_db_context() as db:
            update_session(
                db, session.id,
                state=next_state_after,
                concepts_status=session.concepts_status,
                difficulty_level=session.difficulty_level,
            )

        if next_state_after == DeepLearnState.AWAITING_COMMAND:
            yield _sse("show_commands", {"commands": ["continue", "expand", "skip", "reteach"]})

    async def _handle_assessment(
        self, session: SessionState, user_answer: str, node_name: str, node_why: str
    ) -> AsyncGenerator[str, None]:
        concept = _get_current_concept(session)
        assessment = await self.assessment_agent.evaluate_answer(
            session=session,
            question="（根据当前概念讲解内容）",
            user_answer=user_answer,
            concept=concept,
        )
        yield _sse("assessment", {
            "is_correct": assessment.is_correct,
            "explanation": assessment.explanation,
            "feedback": assessment.feedback,
        })

        # 更新 session 状态
        new_wrong_count = assessment.wrong_count if not assessment.is_correct else 0
        new_weak_points = list(set(session.weak_points + assessment.update_weak_points))
        new_difficulty = max(1, min(5, session.difficulty_level + assessment.difficulty_delta))

        if assessment.is_correct:
            session.concepts_status[concept] = "done"

        result = self.orchestrator.on_assessment_done(
            current_state=DeepLearnState.EVALUATING,
            is_correct=assessment.is_correct,
            wrong_count=new_wrong_count,
            all_concepts_done=_all_concepts_done(session),
        )
        yield _sse("state_change", {"from": "EVALUATING", "to": result.next_state})

        with get_db_context() as db:
            update_session(
                db, session.id,
                state=result.next_state,
                wrong_count_current=new_wrong_count,
                weak_points=new_weak_points,
                difficulty_level=new_difficulty,
                concepts_status=session.concepts_status,
            )

        if result.action == "show_command_prompt":
            yield _sse("show_commands", {"commands": ["continue", "expand", "skip", "reteach"]})
        elif result.action == "run_teaching":
            mode = (result.meta or {}).get("mode", "probe_stuck")
            output = await self.teaching_agent.teach(session, node_name, node_why, _build_memory_context(session), mode)
            async for event in self._stream_teaching_output(session, output, result.next_state):
                yield event

    async def _handle_readiness(self, session: SessionState, node_name: str) -> AsyncGenerator[str, None]:
        readiness = await self.assessment_agent.check_readiness(session, node_name)
        result = self.orchestrator.on_readiness_checked(readiness.ready_for_test)
        yield _sse("state_change", {"from": "AI_ASSESSING_READINESS", "to": result.next_state})

        if readiness.ready_for_test:
            yield _sse("test_confirm_prompt", {
                "message": f"{readiness.reasoning}\n\n你准备好开始综合测试了吗？",
                "commands": ["confirm_test", "not_ready"],
            })
        else:
            review_hint = f"建议复习：{', '.join(readiness.suggest_review_concepts)}" if readiness.suggest_review_concepts else ""
            yield _sse("chunk", {"text": f"{readiness.reasoning}\n\n{review_hint}"})

        with get_db_context() as db:
            update_session(db, session.id, state=result.next_state)

    async def _handle_test_evaluation(
        self, session: SessionState, user_answer: str, node_name: str
    ) -> AsyncGenerator[str, None]:
        assessment = await self.assessment_agent.evaluate_answer(
            session=session,
            question="综合测试",
            user_answer=user_answer,
            concept=node_name,
        )
        result = self.orchestrator.on_assessment_done(
            current_state=DeepLearnState.EVALUATING_TEST,
            is_correct=assessment.is_correct,
            wrong_count=0,
            all_concepts_done=True,
        )
        yield _sse("assessment", {"is_correct": assessment.is_correct, "explanation": assessment.explanation, "feedback": assessment.feedback})
        yield _sse("state_change", {"from": "EVALUATING_TEST", "to": result.next_state})

        if result.next_state == DeepLearnState.COMPLETED:
            yield _sse("chunk", {"text": "🎉 恭喜你通过了本节点的综合测试！"})
            with get_db_context() as db:
                update_session(db, session.id, state=DeepLearnState.COMPLETED, status="completed")
                # 更新节点状态为 learned
                db.execute(
                    "UPDATE nodes SET status = 'learned' WHERE id = ?",
                    (session.node_id,)
                )
                db.commit()
        elif result.action == "show_fail_options":
            yield _sse("fail_options", {
                "message": "这次还没通过，选择下一步：",
                "options": [
                    {"command": "restart", "label": "🔄 从头开始"},
                    {"command": "not_ready", "label": "📚 针对弱点复习"},
                ]
            })
            with get_db_context() as db:
                update_session(db, session.id, state=result.next_state)

    async def _maybe_checkpoint(self, session: SessionState):
        turn_count = len(session.recent_turns)
        if turn_count > 0 and turn_count % _CHECKPOINT_EVERY == 0:
            with get_db_context() as db:
                update_session(db, session.id, recent_turns=session.recent_turns)


def _sse(event_type: str, data: dict) -> str:
    import json as _json
    return f"data: {_json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


_service: Optional[DeepLearnService] = None

def get_deep_learn_service() -> DeepLearnService:
    global _service
    if _service is None:
        _service = DeepLearnService()
    return _service
```

**验收**：`get_or_create_session()` 正常返回；`stream_message()` 对一条用户消息产生至少一个 SSE 事件。

---

## Task 8 — API Router

**文件**：`backend/routers/deep_learn.py`

```python
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from database import get_db, get_db_context
from services.deep_learn.service import get_deep_learn_service
from services.deep_learn.session_repo import get_session_by_id, update_session
from models_deep_learn import CreateSessionRequest, CreateSessionResponse, MessageRequest, CommandRequest
from utils.auth import get_current_user_id

router = APIRouter(prefix="/api/deep-learn", tags=["DeepLearn"])
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _get_node_info(db, node_id: str, user_id: str) -> tuple[str, str, str]:
    """返回 (node_name, node_why, plan_id)，验证归属权"""
    row = db.execute(
        "SELECT n.name, n.why, n.plan_id FROM nodes n "
        "JOIN plans p ON p.id = n.plan_id "
        "WHERE n.id = ? AND p.user_id = ?",
        (node_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NODE_NOT_FOUND", "message": "节点不存在"})
    return row["name"], row["why"] or "", row["plan_id"]


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_or_resume_session(
    req: CreateSessionRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_node_info(db, req.node_id, current_user_id)  # 权限检查
    svc = get_deep_learn_service()
    session, is_resumed = await svc.get_or_create_session(current_user_id, req.node_id, req.plan_id)
    return CreateSessionResponse(
        success=True,
        session_id=session.id,
        state=session.state,
        is_resumed=is_resumed,
        what_list=session.what_list,
        concepts_status=session.concepts_status,
    )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    session = get_session_by_id(db, session_id, current_user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Session 不存在"})
    return {"success": True, "data": session.model_dump()}


@router.post("/sessions/{session_id}/initialize")
async def initialize_session(
    session_id: str,
    http_request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """新 session 的第一条流：Teaching Agent 讲第一个概念"""
    session = get_session_by_id(db, session_id, current_user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Session 不存在"})
    node_name, node_why, _ = _get_node_info(db, session.node_id, current_user_id)

    svc = get_deep_learn_service()

    async def _gen():
        async for chunk in svc.stream_initial(session, node_name, node_why):
            if await http_request.is_disconnected():
                return
            yield chunk

    return StreamingResponse(_gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    req: MessageRequest,
    http_request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    session = get_session_by_id(db, session_id, current_user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Session 不存在"})
    node_name, node_why, _ = _get_node_info(db, session.node_id, current_user_id)

    svc = get_deep_learn_service()

    async def _gen():
        async for chunk in svc.stream_message(session, req.content, node_name, node_why):
            if await http_request.is_disconnected():
                return
            yield chunk

    return StreamingResponse(_gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/sessions/{session_id}/command")
async def send_command(
    session_id: str,
    req: CommandRequest,
    http_request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    session = get_session_by_id(db, session_id, current_user_id)
    if not session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Session 不存在"})
    node_name, node_why, _ = _get_node_info(db, session.node_id, current_user_id)

    svc = get_deep_learn_service()

    async def _gen():
        async for chunk in svc.stream_command(session, req.command, node_name, node_why):
            if await http_request.is_disconnected():
                return
            yield chunk

    return StreamingResponse(_gen(), media_type="text/event-stream", headers=SSE_HEADERS)
```

**验收**：`POST /api/deep-learn/sessions` 返回 `session_id`；`POST /api/deep-learn/sessions/{id}/message` 返回 SSE 流。

---

## Task 9 — 注册 Router

**修改文件**：`backend/main.py`

在 `from routers import ...` 那行加入 `deep_learn`，在 `app.include_router` 部分加一行：

```python
# 在 from routers import ... 行末尾加入
from routers import deep_learn   # 新增

# 在 app.include_router(ai.router) 下面加
app.include_router(deep_learn.router)  # 新增
```

**验收**：`GET /docs` 能看到 `/api/deep-learn/sessions` 路径。

---

## Task 10 — 前端 API Service

**文件**：`frontend/src/services/deepLearnApi.js`

```javascript
import { getAuthHeaders, API_BASE } from './api';  // 复用现有 auth header 工具

const BASE = `${API_BASE}/api/deep-learn`;

export const deepLearnApi = {
  /** 创建或恢复 session */
  createSession: async ({ nodeId, planId }) => {
    const res = await fetch(`${BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ node_id: nodeId, plan_id: planId }),
    });
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
  },

  /** 获取 session 状态 */
  getSession: async (sessionId) => {
    const res = await fetch(`${BASE}/sessions/${sessionId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get session');
    return res.json();
  },

  /**
   * 初始化新 session（返回 SSE ReadableStream）
   * 调用方负责消费流
   */
  initializeSession: (sessionId) =>
    fetch(`${BASE}/sessions/${sessionId}/initialize`, {
      method: 'POST',
      headers: getAuthHeaders(),
    }),

  /** 发送消息（返回 fetch Response，调用方消费 SSE） */
  sendMessage: (sessionId, content) =>
    fetch(`${BASE}/sessions/${sessionId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ content }),
    }),

  /** 发送控制命令 */
  sendCommand: (sessionId, command) =>
    fetch(`${BASE}/sessions/${sessionId}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ command }),
    }),
};
```

> 注意：如果现有 `api.js` 没有导出 `getAuthHeaders` 和 `API_BASE`，在此文件里直接读 localStorage token 即可，参考现有 api.js 的写法。

---

## Task 11 — App.jsx 新增路由

**修改文件**：`frontend/src/App.jsx`

```jsx
// 在 import 区域加入
import DeepLearnPage from './pages/DeepLearnPage';

// 在 <Routes> 内加入（放在 /graph/:planId 路由之后）
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

## Task 12 — DeepLearnPage（骨架）

**文件**：`frontend/src/pages/DeepLearnPage.jsx`

```jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RotateCcw } from 'lucide-react';
import ConceptProgress from '../components/deep-learn/ConceptProgress';
import DeepLearnChat from '../components/deep-learn/DeepLearnChat';
import { useDeepLearnSession } from '../hooks/useDeepLearnSession';

export default function DeepLearnPage() {
  const { planId, nodeId } = useParams();
  const navigate = useNavigate();
  const {
    session,
    messages,
    isStreaming,
    conceptsStatus,
    weakPoints,
    sendMessage,
    sendCommand,
    showCommands,
    showTestConfirm,
    showFailOptions,
  } = useDeepLearnSession({ planId, nodeId });

  if (!session) {
    return (
      <div className="flex items-center justify-center h-screen text-zinc-400">
        正在初始化学习环境...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#FAFAFA] overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 border-b border-zinc-200 bg-white shrink-0">
        <button
          onClick={() => navigate(`/graph/${planId}`)}
          className="flex items-center gap-1 text-zinc-500 hover:text-zinc-800 text-sm"
        >
          <ArrowLeft size={16} /> 返回
        </button>
        <span className="font-medium text-zinc-800 flex-1 truncate">
          深入学习：{session.nodeName || ''}
        </span>
        <button
          onClick={() => sendCommand('restart')}
          className="flex items-center gap-1 text-zinc-400 hover:text-zinc-700 text-sm"
        >
          <RotateCcw size={14} /> 重新开始
        </button>
      </header>

      {/* Main: left + right */}
      <div className="flex flex-1 overflow-hidden">
        {/* 左侧：概念进度 */}
        <aside className="w-64 shrink-0 border-r border-zinc-200 bg-white overflow-y-auto">
          <ConceptProgress
            whatList={session.whatList}
            conceptsStatus={conceptsStatus}
            weakPoints={weakPoints}
          />
        </aside>

        {/* 右侧：对话区 */}
        <main className="flex-1 overflow-hidden">
          <DeepLearnChat
            messages={messages}
            isStreaming={isStreaming}
            showCommands={showCommands}
            showTestConfirm={showTestConfirm}
            showFailOptions={showFailOptions}
            onSendMessage={sendMessage}
            onSendCommand={sendCommand}
          />
        </main>
      </div>
    </div>
  );
}
```

---

## Task 13 — ConceptProgress 组件

**文件**：`frontend/src/components/deep-learn/ConceptProgress.jsx`

```jsx
import React from 'react';
import { CheckCircle2, Circle, ChevronRight, SkipForward, AlertTriangle } from 'lucide-react';

const STATUS_CONFIG = {
  done:    { icon: CheckCircle2, color: 'text-emerald-500', bg: 'bg-emerald-50' },
  current: { icon: ChevronRight,  color: 'text-blue-500',   bg: 'bg-blue-50'    },
  skipped: { icon: SkipForward,   color: 'text-zinc-400',   bg: 'bg-zinc-50'    },
  pending: { icon: Circle,        color: 'text-zinc-300',   bg: ''              },
};

export default function ConceptProgress({ whatList = [], conceptsStatus = {}, weakPoints = [] }) {
  const done   = Object.values(conceptsStatus).filter(s => s === 'done').length;
  const total  = whatList.length;
  const pct    = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="p-4 space-y-5">
      {/* 进度条 */}
      <div>
        <div className="flex justify-between text-xs text-zinc-400 mb-1">
          <span>学习进度</span>
          <span>{done}/{total}</span>
        </div>
        <div className="h-1.5 bg-zinc-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-400 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* 概念列表 */}
      <div className="space-y-1.5">
        <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">概念列表</p>
        {whatList.map((concept, i) => {
          const status = conceptsStatus[concept] || 'pending';
          const { icon: Icon, color, bg } = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
          return (
            <div
              key={i}
              className={`flex items-start gap-2 p-2 rounded-lg text-sm ${bg}`}
            >
              <Icon size={14} className={`mt-0.5 shrink-0 ${color}`} />
              <span className={status === 'pending' ? 'text-zinc-400' : 'text-zinc-700'}>
                {concept}
              </span>
            </div>
          );
        })}
      </div>

      {/* 弱点追踪 */}
      {weakPoints.length > 0 && (
        <div>
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">弱点追踪</p>
          <div className="space-y-1">
            {weakPoints.map((wp, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 rounded-lg p-2">
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                <span>{wp}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## Task 14 — DeepLearnChat 组件

**文件**：`frontend/src/components/deep-learn/DeepLearnChat.jsx`

```jsx
import React, { useRef, useEffect, useState } from 'react';
import { Send } from 'lucide-react';
import ChatMarkdownMessage from '../chat/ChatMarkdownMessage';  // 复用现有组件
import CommandBar from './CommandBar';
import MermaidDiagram from './MermaidDiagram';

export default function DeepLearnChat({
  messages = [],
  isStreaming = false,
  showCommands = false,
  showTestConfirm = null,
  showFailOptions = null,
  onSendMessage,
  onSendCommand,
}) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    onSendMessage(text);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[70%] bg-zinc-800 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                {msg.content}
              </div>
            ) : msg.type === 'mermaid' ? (
              <div className="max-w-[85%]">
                <MermaidDiagram code={msg.content} />
              </div>
            ) : (
              <div className="max-w-[85%]">
                <ChatMarkdownMessage content={msg.content} />
              </div>
            )}
          </div>
        ))}
        {isStreaming && (
          <div className="flex justify-start">
            <div className="flex gap-1 px-4 py-3">
              {[0,1,2].map(i => (
                <span key={i} className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 控制按钮区 */}
      {showTestConfirm && (
        <div className="px-6 pb-2">
          <div className="bg-blue-50 rounded-xl p-4 text-sm text-blue-800 space-y-3">
            <p>{showTestConfirm.message}</p>
            <CommandBar
              commands={['confirm_test', 'not_ready']}
              onCommand={onSendCommand}
            />
          </div>
        </div>
      )}
      {showFailOptions && (
        <div className="px-6 pb-2">
          <div className="bg-amber-50 rounded-xl p-4 text-sm text-amber-800 space-y-3">
            <p>{showFailOptions.message}</p>
            <CommandBar
              commands={showFailOptions.options.map(o => o.command)}
              labels={Object.fromEntries(showFailOptions.options.map(o => [o.command, o.label]))}
              onCommand={onSendCommand}
            />
          </div>
        </div>
      )}
      {showCommands && !showTestConfirm && !showFailOptions && (
        <div className="px-6 pb-2">
          <CommandBar commands={['continue', 'expand', 'skip', 'reteach']} onCommand={onSendCommand} />
        </div>
      )}

      {/* 输入框 */}
      <div className="px-6 pb-6 pt-2 border-t border-zinc-100">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder="输入你的回答，或直接输入「继续」「展开」等指令…"
            className="flex-1 resize-none rounded-xl border border-zinc-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-300 bg-white"
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="self-end p-2.5 rounded-xl bg-zinc-800 text-white disabled:opacity-40 hover:bg-zinc-700 transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## Task 15 — CommandBar 组件

**文件**：`frontend/src/components/deep-learn/CommandBar.jsx`

```jsx
import React from 'react';

const COMMAND_LABELS = {
  continue:     '继续 →',
  expand:       '展开',
  skip:         '跳过',
  reteach:      '重讲',
  confirm_test: '✅ 开始测试',
  not_ready:    '再复习一下',
  restart:      '🔄 重新开始',
};

export default function CommandBar({ commands = [], labels = {}, onCommand }) {
  return (
    <div className="flex flex-wrap gap-2">
      {commands.map(cmd => (
        <button
          key={cmd}
          onClick={() => onCommand(cmd)}
          className="px-3 py-1.5 rounded-lg text-sm border border-zinc-200 bg-white hover:bg-zinc-50
                     text-zinc-700 hover:text-zinc-900 transition-colors"
        >
          {labels[cmd] || COMMAND_LABELS[cmd] || cmd}
        </button>
      ))}
    </div>
  );
}
```

---

## Task 16 — MermaidDiagram 组件

**文件**：`frontend/src/components/deep-learn/MermaidDiagram.jsx`

先安装依赖：`npm install mermaid`

```jsx
import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });

let _id = 0;
const nextId = () => `mermaid-${++_id}`;

export default function MermaidDiagram({ code }) {
  const ref = useRef(null);
  const idRef = useRef(nextId());

  useEffect(() => {
    if (!ref.current || !code) return;
    const id = idRef.current;
    mermaid.render(id, code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg;
    }).catch(() => {
      if (ref.current) ref.current.textContent = '[图表渲染失败]';
    });
  }, [code]);

  return (
    <div
      ref={ref}
      className="my-3 p-4 bg-zinc-50 rounded-xl border border-zinc-200 overflow-x-auto"
    />
  );
}
```

---

## Task 17 — useDeepLearnSession Hook

**文件**：`frontend/src/hooks/useDeepLearnSession.js`

```javascript
import { useState, useEffect, useCallback, useRef } from 'react';
import { deepLearnApi } from '../services/deepLearnApi';

function parseSSELine(line) {
  if (!line.startsWith('data: ')) return null;
  try { return JSON.parse(line.slice(6)); } catch { return null; }
}

async function consumeSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      const event = parseSSELine(line.trim());
      if (event) onEvent(event);
    }
  }
}

export function useDeepLearnSession({ planId, nodeId }) {
  const [session, setSession]           = useState(null);
  const [messages, setMessages]         = useState([]);
  const [isStreaming, setIsStreaming]   = useState(false);
  const [conceptsStatus, setConceptsStatus] = useState({});
  const [weakPoints, setWeakPoints]     = useState([]);
  const [showCommands, setShowCommands] = useState(false);
  const [showTestConfirm, setShowTestConfirm] = useState(null);
  const [showFailOptions, setShowFailOptions] = useState(null);

  const sessionIdRef = useRef(null);
  const streamingTextRef = useRef('');

  const appendChunk = useCallback((text) => {
    streamingTextRef.current += text;
    setMessages(prev => {
      const last = prev[prev.length - 1];
      if (last?.role === 'assistant' && last?.streaming) {
        return [...prev.slice(0, -1), { ...last, content: streamingTextRef.current }];
      }
      return [...prev, { role: 'assistant', content: text, streaming: true }];
    });
  }, []);

  const finalizeStream = useCallback(() => {
    streamingTextRef.current = '';
    setMessages(prev => prev.map(m => m.streaming ? { ...m, streaming: false } : m));
    setIsStreaming(false);
  }, []);

  const handleEvent = useCallback((event) => {
    switch (event.type) {
      case 'chunk':
        appendChunk(event.text);
        break;
      case 'image_mermaid':
        setMessages(prev => [...prev, { role: 'assistant', type: 'mermaid', content: event.code }]);
        break;
      case 'questions':
        // questions 已经在 chunk 里渲染，这里更新 state 用于 UI
        break;
      case 'assessment':
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `**${event.is_correct ? '✅' : '❌'} ${event.explanation}**\n\n${event.feedback}`,
        }]);
        break;
      case 'show_commands':
        setShowCommands(true);
        setShowTestConfirm(null);
        setShowFailOptions(null);
        break;
      case 'test_confirm_prompt':
        setShowTestConfirm(event);
        setShowCommands(false);
        break;
      case 'fail_options':
        setShowFailOptions(event);
        setShowCommands(false);
        break;
      case 'concept_update':
        setConceptsStatus(prev => ({ ...prev, [event.concept]: event.status }));
        break;
      case 'state_change':
        setSession(prev => prev ? { ...prev, state: event.to } : prev);
        break;
      case 'done':
        finalizeStream();
        break;
      case 'restart':
        window.location.reload();
        break;
    }
  }, [appendChunk, finalizeStream]);

  const runSSE = useCallback(async (responsePromise) => {
    setIsStreaming(true);
    setShowCommands(false);
    try {
      const response = await responsePromise;
      if (!response.ok) throw new Error('SSE request failed');
      await consumeSSE(response, handleEvent);
    } catch (err) {
      console.error('SSE error', err);
      finalizeStream();
    }
  }, [handleEvent, finalizeStream]);

  // 初始化 session
  useEffect(() => {
    if (!planId || !nodeId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await deepLearnApi.createSession({ nodeId, planId });
        if (cancelled) return;
        sessionIdRef.current = res.session_id;
        setSession({ ...res, nodeName: '', whatList: res.what_list });
        setConceptsStatus(res.concepts_status || {});

        if (!res.is_resumed) {
          // 新 session：触发第一次讲解
          await runSSE(deepLearnApi.initializeSession(res.session_id));
        }
        // 恢复 session：展示恢复提示，等待用户输入
        if (res.is_resumed) {
          setMessages([{ role: 'assistant', content: '**已恢复上次学习进度。** 你可以继续提问，或点击"继续"进入下一个概念。' }]);
          setShowCommands(true);
        }
      } catch (err) {
        console.error('Failed to init session', err);
      }
    })();
    return () => { cancelled = true; };
  }, [planId, nodeId]);

  const sendMessage = useCallback(async (content) => {
    if (!sessionIdRef.current || isStreaming) return;
    setMessages(prev => [...prev, { role: 'user', content }]);
    setShowCommands(false);
    await runSSE(deepLearnApi.sendMessage(sessionIdRef.current, content));
  }, [isStreaming, runSSE]);

  const sendCommand = useCallback(async (command) => {
    if (!sessionIdRef.current || isStreaming) return;
    setShowCommands(false);
    setShowTestConfirm(null);
    setShowFailOptions(null);
    await runSSE(deepLearnApi.sendCommand(sessionIdRef.current, command));
  }, [isStreaming, runSSE]);

  return {
    session,
    messages,
    isStreaming,
    conceptsStatus,
    weakPoints,
    showCommands,
    showTestConfirm,
    showFailOptions,
    sendMessage,
    sendCommand,
  };
}
```

---

## 新增文件清单（Phase 1）

```
backend/
  scripts/migration_deep_learn_sessions.sql   ← Task 1（在 Supabase 执行）
  models_deep_learn.py                        ← Task 2
  services/deep_learn/__init__.py             ← 空文件
  services/deep_learn/session_repo.py         ← Task 3
  services/deep_learn/orchestrator.py         ← Task 4
  services/deep_learn/teaching_agent.py       ← Task 5B
  services/deep_learn/assessment_agent.py     ← Task 6B
  services/deep_learn/service.py              ← Task 7
  routers/deep_learn.py                       ← Task 8
  services/llm/configs/deep_learn_teaching.json   ← Task 5A
  services/llm/configs/deep_learn_assessment.json ← Task 6A

frontend/
  src/services/deepLearnApi.js                ← Task 10
  src/hooks/useDeepLearnSession.js            ← Task 17
  src/pages/DeepLearnPage.jsx                 ← Task 12
  src/components/deep-learn/ConceptProgress.jsx ← Task 13
  src/components/deep-learn/DeepLearnChat.jsx   ← Task 14
  src/components/deep-learn/CommandBar.jsx      ← Task 15
  src/components/deep-learn/MermaidDiagram.jsx  ← Task 16

修改文件：
  backend/main.py        ← Task 9（加 include_router）
  frontend/src/App.jsx   ← Task 11（加路由）
```

## 完成标志（Phase 1 done）

- [ ] 用户能从节点详情页进入深入学习工作台
- [ ] Teaching Agent 讲完第一个概念后出题
- [ ] 用户回答后 Assessment Agent 给出评估
- [ ] 四个控制按钮（继续/展开/跳过/重讲）功能正常
- [ ] 概念进度列表左侧实时更新
- [ ] 关闭页面后重新进入，session 自动恢复
- [ ] 综合测试通过后节点状态变为 `learned`
