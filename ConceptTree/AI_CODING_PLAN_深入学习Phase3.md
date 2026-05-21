# AI Coding Plan — 深入学习工作台 Phase 3

> Source of truth: PRD_深入学习工作台.md §九 Phase 3  
> Codebase root: `backend/` and `frontend/src/`  
> Execution order: Tasks labeled B-01–B-08 (backend) and F-01–F-05 (frontend).  
> Dependencies are explicit. Do not begin a task until all its dependencies are complete.  
> **Phase 2 must be fully merged and tests passing before starting Phase 3.**

---

## CONTEXT SNAPSHOT

### Phase 2 end state (foundation Phase 3 builds on)

```python
# backend/models_deep_learn.py
DeepLearnState = Literal[
    "INITIALIZING", "TEACHING", "QUESTIONING", "EVALUATING", "AWAITING_COMMAND",
    "AI_ASSESSING_READINESS", "CONFIRMING_TEST", "TESTING", "EVALUATING_TEST",
    "CHOOSING_AFTER_FAIL", "COMPLETED",
]
```

```python
# backend/services/deep_learn/state_machine.py — current (Phase 2)
def decide_on_final_judge(passed: bool) -> Decision:
    if passed:
        return Decision(next_state="COMPLETED", action="mark_node_learned")
    return Decision(next_state="CHOOSING_AFTER_FAIL", action="show_fail_options")
```

```python
# backend/services/deep_learn/service.py — _run_final_judge (Phase 2)
if decision.action == "mark_node_learned":
    with get_db_context() as db:
        db.execute("UPDATE nodes SET status='learned' WHERE id=?", (session.node_id,))
        db.commit()
        update_session(db, session.id, state="COMPLETED", status="completed",
                       ended_at=datetime.now(timezone.utc))
    yield _sse("state_change", **{"from": session.state, "to": "COMPLETED"})
    session.state = "COMPLETED"
    yield _sse("node_completed", node_id=session.node_id)
    # + memory fire for test_passed
```

### Phase 3 target: what changes

When the user passes the final test, the flow becomes:

```
EVALUATING_TEST → decide_on_final_judge(passed=True)
  → Decision(next_state="GENERATING_NOTE", action="generate_note")
  → _run_final_judge emits note_generating SSE
  → NoteGeneratorAgent.generate(session, node_meta) → markdown string
  → save to completion_notes table → returns note_id
  → marks node learned + session COMPLETED (same as before)
  → emits note_ready SSE with note_id
  → frontend shows "完成笔记 ↗" button in Header
  → user clicks → /deep-learn/:planId/:nodeId/note/:noteId (zhihu-style page + PDF)
```

### New SSE events introduced in Phase 3

```jsonc
{"type": "note_generating"}                        // emitted immediately, triggers loading state
{"type": "note_ready", "note_id": "<uuid>"}        // emitted after note saved to DB
```

### New backend route

```
GET /api/deep-learn/notes/{note_id}
→ { "id": "uuid", "content": "markdown", "node_id": "...", "created_at": "..." }
```

### New frontend route

```
/deep-learn/:planId/:nodeId/note/:noteId   →  CompletionNotePage
```

### Key existing patterns to follow

- DB calls: `with get_db_context() as db:` + `db.execute("...", (...,))` with `?` placeholders
- SSE: `_sse(event_type, **data)` → `f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"`
- LLM configs: JSON file with `model_params` + `system_prompt` keys, loaded via `load_ai_config(name, user_prompt, **kwargs)`
- Agent pattern: class with `async def method(self, **kwargs)` that calls `self.llm_client.chat_json(...)` or `chat_stream(...)`
- Memory fires: always inside `try/except`, never raise, use `background_tasks`
- All DB write failures in memory layer: catch + log, never propagate

---

## TASK DEPENDENCY GRAPH

```
B-01 ──► B-02 ──► B-03 ──┐
                           ├──► B-07 ──► B-08
B-04 ──► B-05 ─────────────┘
B-02 ──► B-06 ──────────────► B-07

F-01 ──► F-02
F-03 ──► F-04
F-03 ──► F-05
```

All F tasks require B-07 (note_ready SSE) and B-08 (note fetch endpoint) to be implemented first.

---

## BACKEND TASKS

---

### B-01 — DB migration SQL

**File to create:** `backend/sql/2026-05-21_completion_notes.sql`

**Purpose:** Create `completion_notes` table and extend the `deep_learn_sessions` state constraint to include `GENERATING_NOTE`. Execute manually in Supabase SQL Editor — do NOT run from Python.

**Exact file content:**

```sql
-- Phase 3: Completion notes storage
CREATE TABLE IF NOT EXISTS completion_notes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL,
  node_id     TEXT NOT NULL,
  session_id  UUID NOT NULL REFERENCES deep_learn_sessions(id),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_completion_notes_session
  ON completion_notes(session_id);

-- Extend the state constraint to include GENERATING_NOTE
ALTER TABLE deep_learn_sessions
  DROP CONSTRAINT IF EXISTS dl_sessions_state_check;

ALTER TABLE deep_learn_sessions
  ADD CONSTRAINT dl_sessions_state_check CHECK (state IN (
    'INITIALIZING','TEACHING','QUESTIONING','EVALUATING','AWAITING_COMMAND',
    'AI_ASSESSING_READINESS','CONFIRMING_TEST','TESTING','EVALUATING_TEST',
    'CHOOSING_AFTER_FAIL','GENERATING_NOTE','COMPLETED'
  ));
```

**Acceptance criteria:**
- File is valid SQL, parseable without error
- `completion_notes` table has columns: id, user_id, node_id, session_id, content, created_at
- `GENERATING_NOTE` is included in the state constraint
- **Manual step**: execute this SQL in Supabase SQL Editor before running any backend code

---

### B-02 — Pydantic models

**File to modify:** `backend/models_deep_learn.py`

**Change 1:** Add `"GENERATING_NOTE"` to `DeepLearnState`.

Find:
```python
DeepLearnState = Literal[
    "INITIALIZING", "TEACHING", "QUESTIONING", "EVALUATING", "AWAITING_COMMAND",
    "AI_ASSESSING_READINESS", "CONFIRMING_TEST", "TESTING", "EVALUATING_TEST",
    "CHOOSING_AFTER_FAIL", "COMPLETED",
]
```

Replace with:
```python
DeepLearnState = Literal[
    "INITIALIZING", "TEACHING", "QUESTIONING", "EVALUATING", "AWAITING_COMMAND",
    "AI_ASSESSING_READINESS", "CONFIRMING_TEST", "TESTING", "EVALUATING_TEST",
    "CHOOSING_AFTER_FAIL", "GENERATING_NOTE", "COMPLETED",
]
```

**Change 2:** Append new models at the end of `backend/models_deep_learn.py`:

```python
class NoteGeneratorOutput(BaseModel):
    content: str  # Full markdown of the completion note


class CompletionNote(BaseModel):
    id: str
    user_id: str
    node_id: str
    session_id: str
    content: str
    created_at: str
```

**Acceptance criteria:**
- `from models_deep_learn import DeepLearnState, NoteGeneratorOutput, CompletionNote` succeeds
- `"GENERATING_NOTE" in DeepLearnState.__args__` is True
- `NoteGeneratorOutput(content="test").content == "test"`

---

### B-03 — completion_notes repository

**File to create:** `backend/services/deep_learn/notes_repo.py`

**Purpose:** CRUD for `completion_notes` table. All write failures must be caught and logged — never raise to caller.

**Exact file content:**

```python
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def save_completion_note(
    db,
    *,
    user_id: str,
    node_id: str,
    session_id: str,
    content: str,
) -> Optional[str]:
    """Insert a completion note. Returns the new note UUID, or None on failure."""
    try:
        db.execute(
            """
            INSERT INTO completion_notes (user_id, node_id, session_id, content)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, node_id, session_id, content),
        )
        db.commit()
        row = db.execute(
            "SELECT id FROM completion_notes WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return str(row["id"]) if row else None
    except Exception:
        logger.exception("save_completion_note failed (non-fatal)")
        return None


def get_completion_note_by_id(db, note_id: str) -> Optional[dict]:
    """Fetch a completion note by its UUID. Returns None if not found."""
    try:
        row = db.execute(
            "SELECT id, user_id, node_id, session_id, content, created_at FROM completion_notes WHERE id=?",
            (note_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "node_id": row["node_id"],
            "session_id": str(row["session_id"]),
            "content": row["content"],
            "created_at": str(row["created_at"]),
        }
    except Exception:
        logger.exception("get_completion_note_by_id failed")
        return None


def get_completion_note_by_session(db, session_id: str) -> Optional[dict]:
    """Fetch the completion note for a session. Returns None if not found."""
    try:
        row = db.execute(
            "SELECT id, user_id, node_id, session_id, content, created_at FROM completion_notes WHERE session_id=? LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "node_id": row["node_id"],
            "session_id": str(row["session_id"]),
            "content": row["content"],
            "created_at": str(row["created_at"]),
        }
    except Exception:
        logger.exception("get_completion_note_by_session failed")
        return None
```

**Acceptance criteria:**
- `from services.deep_learn.notes_repo import save_completion_note, get_completion_note_by_id, get_completion_note_by_session` succeeds
- All functions accept `db` as first positional arg
- `save_completion_note` returns `None` (not raises) if DB write fails
- `get_completion_note_by_id` returns `None` (not raises) if note not found or DB error

---

### B-04 — Note Generator LLM config

**File to create:** `backend/services/llm/configs/deep_learn_note_gen.json`

**Purpose:** Prompt config for the NoteGeneratorAgent. Produces a zhihu-style personal learning summary in Markdown, based on the user's session history, weak points, and what was covered.

**Exact file content:**

```json
{
  "model_params": {
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "system_prompt": "你是一位帮助用户整理学习笔记的助手。根据用户本次深度学习的完整记录，生成一份知乎风格的个人学习总结笔记。\n\n节点主题：{{node_name}}\n学习目标：{{node_why}}\n\n要求：\n1. 风格：个人第一人称，像知乎专栏文章，有叙述性而非教科书式。\n2. 结构：开篇一句话点题 → 核心概念梳理（结合本次覆盖的主题）→ 我的理解与类比 → 踩坑与突破（结合弱点记录）→ 收获总结。\n3. 长度：600-1200 字，使用 Markdown 格式（#/##/- /> 等），允许插入代码块。\n4. 只输出笔记正文，不要输出 JSON，不要有任何包裹结构。\n5. 若存在弱点记录，必须在"踩坑与突破"部分提及并说明如何解决。\n6. 语言：中文。"
}
```

**Acceptance criteria:**
- File is valid JSON
- `json.load()` succeeds
- `system_prompt` contains `{{node_name}}` and `{{node_why}}` placeholders
- `load_ai_config("deep_learn_note_gen", "user_prompt_here", node_name="X", node_why="Y")` returns without error

---

### B-05 — NoteGeneratorAgent

**File to create:** `backend/services/deep_learn/agents/note_generator.py`

**Purpose:** Calls the LLM to generate a zhihu-style markdown completion note. Returns a `NoteGeneratorOutput`. Uses `chat_json` is NOT appropriate here — the output is raw markdown, so use `chat` (non-streaming, returns plain text). If the LLM client does not have a `chat` method for plain text, use `chat_stream` and collect chunks.

**Exact file content:**

```python
from __future__ import annotations

import logging

from models_deep_learn import NoteGeneratorOutput, SessionState
from services.llm.configs import load_ai_config
from services.llm.client import get_llm_client

logger = logging.getLogger(__name__)

_MAX_TURNS_FOR_NOTE = 20  # cap recent_turns to avoid exceeding token budget


class NoteGeneratorAgent:
    def __init__(self) -> None:
        self.llm_client = get_llm_client()

    async def generate(
        self,
        *,
        session: SessionState,
        node_name: str,
        node_why: str,
    ) -> NoteGeneratorOutput:
        concepts_covered = [
            session.what_list[i]
            for i in range(len(session.what_list))
            if session.concepts_status.get(str(i)) in ("done", "skipped")
        ]
        weak_points = session.weak_points

        # Build a concise user prompt from session history
        turns_summary = _summarize_turns(session.recent_turns)

        user_prompt = (
            f"本次学习覆盖的概念：{', '.join(concepts_covered) or '（无记录）'}\n"
            f"弱点记录：{', '.join(weak_points) or '（无）'}\n"
            f"对话摘要：\n{turns_summary}"
        )

        params, sys_prompt, usr_prompt = load_ai_config(
            "deep_learn_note_gen",
            user_prompt,
            node_name=node_name,
            node_why=node_why or "深入理解该知识点",
        )

        # Use streaming and collect all chunks into a single string
        content_parts: list[str] = []
        async for chunk in self.llm_client.chat_stream(
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            temperature=params.get("temperature", 0.7),
            max_tokens=params.get("max_tokens", 2000),
        ):
            if chunk.get("type") == "content":
                content_parts.append(chunk.get("text", ""))

        content = "".join(content_parts).strip()
        if not content:
            content = f"# {node_name} 学习笔记\n\n本次深度学习已完成。\n\n覆盖概念：{', '.join(concepts_covered)}"

        return NoteGeneratorOutput(content=content)


def _summarize_turns(recent_turns: list[dict], max_turns: int = _MAX_TURNS_FOR_NOTE) -> str:
    """Convert recent_turns to a compact text summary for the note generator prompt."""
    if not recent_turns:
        return "（无对话记录）"
    capped = recent_turns[-max_turns:]
    lines: list[str] = []
    for turn in capped:
        role = turn.get("role", "unknown")
        kind = turn.get("kind", "text")
        content = turn.get("content", "")
        if kind in ("mermaid", "dalle_image", "dalle_pending"):
            continue  # skip image turns
        if isinstance(content, list):
            content = " / ".join(str(c) for c in content)
        prefix = "AI" if role == "assistant" else "用户"
        lines.append(f"{prefix}: {str(content)[:200]}")
    return "\n".join(lines) or "（无文字对话记录）"
```

**Acceptance criteria:**
- `from services.deep_learn.agents.note_generator import NoteGeneratorAgent` succeeds
- `NoteGeneratorAgent` has `async def generate(self, *, session, node_name, node_why)` method
- Returns `NoteGeneratorOutput` with non-empty `content`
- `_summarize_turns([])` returns `"（无对话记录）"` without error
- If LLM returns empty content, fallback string is used (never raises, never returns empty string)

---

### B-06 — State machine: add GENERATING_NOTE

**File to modify:** `backend/services/deep_learn/state_machine.py`

**Change 1:** Add `"generate_note"` to the `action` Literal in `Decision`.

Find:
```python
    action: Literal[
        "teach", "wait_user", "emit_questions",
        "assess_per_question", "show_commands",
        "check_readiness", "show_test_confirm",
        "generate_test_questions", "emit_next_test_q",
        "final_judge", "mark_node_learned", "show_fail_options",
        "abandon_and_restart",
    ]
```

Replace with:
```python
    action: Literal[
        "teach", "wait_user", "emit_questions",
        "assess_per_question", "show_commands",
        "check_readiness", "show_test_confirm",
        "generate_test_questions", "emit_next_test_q",
        "final_judge", "generate_note", "show_fail_options",
        "abandon_and_restart",
    ]
```

**Change 2:** Modify `decide_on_final_judge` to route through `GENERATING_NOTE` on pass.

Find:
```python
def decide_on_final_judge(passed: bool) -> Decision:
    if passed:
        return Decision(next_state="COMPLETED", action="mark_node_learned")
    return Decision(next_state="CHOOSING_AFTER_FAIL", action="show_fail_options")
```

Replace with:
```python
def decide_on_final_judge(passed: bool) -> Decision:
    if passed:
        return Decision(next_state="GENERATING_NOTE", action="generate_note")
    return Decision(next_state="CHOOSING_AFTER_FAIL", action="show_fail_options")
```

**Acceptance criteria:**
- `decide_on_final_judge(True).action == "generate_note"`
- `decide_on_final_judge(True).next_state == "GENERATING_NOTE"`
- `decide_on_final_judge(False).action == "show_fail_options"` (unchanged)
- `Decision` dataclass instantiates with `action="generate_note"` without ValueError

---

### B-07 — service.py: handle generate_note action

**File to modify:** `backend/services/deep_learn/service.py`

**Change 1:** Add imports at the top of the file (after existing imports):

```python
from services.deep_learn.agents.note_generator import NoteGeneratorAgent
from services.deep_learn.notes_repo import save_completion_note
```

**Change 2:** Add `self.note_generator = NoteGeneratorAgent()` inside `DeepLearnService.__init__`.

Find the `__init__` method body (it initializes `self.teaching_agent`, `self.assessment_per_q`, etc.) and add:
```python
        self.note_generator = NoteGeneratorAgent()
```

**Change 3:** In `_run_final_judge`, replace the entire `if decision.action == "mark_node_learned":` block.

Find:
```python
        if decision.action == "mark_node_learned":
            with get_db_context() as db:
                db.execute("UPDATE nodes SET status='learned' WHERE id=?", (session.node_id,))
                db.commit()
                update_session(db, session.id,
                               state="COMPLETED",
                               status="completed",
                               ended_at=datetime.now(timezone.utc))
            yield _sse("state_change", **{"from": session.state, "to": "COMPLETED"})
            session.state = "COMPLETED"
            yield _sse("node_completed", node_id=session.node_id)
            # Memory: test passed
            self.memory_updater.fire(
                MemoryEvent(
                    user_id=session.user_id, session_id=session.id, node_id=session.node_id,
                    event_type="test_passed",
                    payload={
                        "plan_id": session.plan_id,
                        "concepts_covered": concepts_covered,
                        "weak_points": session.weak_points,
                        "test_results": session.test_results,
                        "conversation_turns": len(session.recent_turns),
                    },
                ),
                background_tasks,
            )
```

Replace with:
```python
        if decision.action == "generate_note":
            # Transition to GENERATING_NOTE immediately
            with get_db_context() as db:
                update_session(db, session.id, state="GENERATING_NOTE")
            yield _sse("state_change", **{"from": session.state, "to": "GENERATING_NOTE"})
            session.state = "GENERATING_NOTE"
            yield _sse("note_generating")

            # Generate the completion note
            note_id: Optional[str] = None
            try:
                note_output = await self.note_generator.generate(
                    session=session,
                    node_name=node_meta.get("node_name", ""),
                    node_why=node_meta.get("node_why", ""),
                )
                with get_db_context() as db:
                    note_id = save_completion_note(
                        db,
                        user_id=session.user_id,
                        node_id=session.node_id,
                        session_id=session.id,
                        content=note_output.content,
                    )
            except Exception:
                logger.exception("Note generation failed (non-fatal) — completing session without note")

            # Mark node learned and complete session
            with get_db_context() as db:
                db.execute("UPDATE nodes SET status='learned' WHERE id=?", (session.node_id,))
                db.commit()
                update_session(db, session.id,
                               state="COMPLETED",
                               status="completed",
                               ended_at=datetime.now(timezone.utc))
            yield _sse("state_change", **{"from": "GENERATING_NOTE", "to": "COMPLETED"})
            session.state = "COMPLETED"

            if note_id:
                yield _sse("note_ready", note_id=note_id)

            yield _sse("node_completed", node_id=session.node_id)

            # Memory: test passed
            self.memory_updater.fire(
                MemoryEvent(
                    user_id=session.user_id, session_id=session.id, node_id=session.node_id,
                    event_type="test_passed",
                    payload={
                        "plan_id": session.plan_id,
                        "concepts_covered": concepts_covered,
                        "weak_points": session.weak_points,
                        "test_results": session.test_results,
                        "conversation_turns": len(session.recent_turns),
                    },
                ),
                background_tasks,
            )
```

**Acceptance criteria:**
- `DeepLearnService` has `self.note_generator` attribute
- When test passes, `_run_final_judge` emits events in order: `state_change(→GENERATING_NOTE)`, `note_generating`, `state_change(→COMPLETED)`, `note_ready` (if note saved), `node_completed`
- If NoteGeneratorAgent raises, session still completes (exception caught, logged, not propagated)
- If `save_completion_note` returns None (DB fail), `note_ready` is NOT emitted but session still completes
- `decide_on_final_judge(False)` path is unchanged

---

### B-08 — Router: GET /notes/{note_id}

**File to modify:** `backend/routers/deep_learn.py`

**Change 1:** Add import at top of router file (after existing imports):

```python
from services.deep_learn.notes_repo import get_completion_note_by_id
```

**Change 2:** Add the new endpoint. Insert after the existing command endpoint (before any module-level code or `app.include_router` calls):

```python
@router.get("/notes/{note_id}")
async def get_completion_note(
    note_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """
    Fetch a completion note by ID.
    Returns 404 if not found, 403 if the note does not belong to the requesting user.
    """
    note = get_completion_note_by_id(db, note_id)
    if not note:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Note not found")
    if note["user_id"] != current_user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "id": note["id"],
        "node_id": note["node_id"],
        "session_id": note["session_id"],
        "content": note["content"],
        "created_at": note["created_at"],
    }
```

**Acceptance criteria:**
- `GET /api/deep-learn/notes/{note_id}` is a registered route (visible in `/docs`)
- Returns 200 with `{id, node_id, session_id, content, created_at}` for valid owned note
- Returns 404 for unknown note_id
- Returns 403 when note exists but belongs to another user
- Does NOT expose `user_id` in the response body

---

## FRONTEND TASKS

---

### F-01 — useDeepLearnSession.js: handle Phase 3 SSE events

**File to modify:** `frontend/src/hooks/useDeepLearnSession.js`

**Purpose:** Track `note_generating` and `note_ready` SSE events. Expose `noteId` and `isGeneratingNote` state to the page.

**Change 1:** Add state variables inside the hook (alongside existing `pinnedImages`, `noteSuggestion`, etc.):

```js
const [noteId, setNoteId] = useState(null);           // UUID string when note is ready
const [isGeneratingNote, setIsGeneratingNote] = useState(false);
```

**Change 2:** In the SSE event switch/if block, add handlers for the two new event types. Insert alongside existing event handlers (e.g. after `image_dalle_done` handler):

```js
case 'note_generating':
  setIsGeneratingNote(true);
  break;

case 'note_ready':
  setIsGeneratingNote(false);
  setNoteId(event.note_id);
  break;
```

**Change 3:** Export `noteId` and `isGeneratingNote` from the hook's return object:

```js
return {
  // ... existing exports ...
  noteId,
  isGeneratingNote,
};
```

**Acceptance criteria:**
- `useDeepLearnSession` returns `noteId` (initially `null`) and `isGeneratingNote` (initially `false`)
- After receiving `note_generating` SSE: `isGeneratingNote === true`, `noteId === null`
- After receiving `note_ready` SSE with `note_id: "abc"`: `isGeneratingNote === false`, `noteId === "abc"`
- Existing behavior for all other SSE events is unchanged

---

### F-02 — DeepLearnPage: "完成笔记 ↗" button in Header

**File to modify:** `frontend/src/pages/DeepLearnPage.jsx`

**Change 1:** Destructure `noteId` and `isGeneratingNote` from `useDeepLearnSession`:

Find:
```js
  const {
    session, messages, conceptsStatus, weakPoints, isStreaming,
    isInitializing, canSendMessage, uiFlags, sendMessage, sendCommand, error,
    pinnedImages, pinImage, unpinImage, noteSuggestion, dismissNoteSuggestion,
  } = useDeepLearnSession({ planId, nodeId });
```

Replace with:
```js
  const {
    session, messages, conceptsStatus, weakPoints, isStreaming,
    isInitializing, canSendMessage, uiFlags, sendMessage, sendCommand, error,
    pinnedImages, pinImage, unpinImage, noteSuggestion, dismissNoteSuggestion,
    noteId, isGeneratingNote,
  } = useDeepLearnSession({ planId, nodeId });
```

**Change 2:** Modify the `Header` component (defined inside `DeepLearnPage.jsx`) to accept and render the note button. The `Header` function currently accepts `{ nodeName, onBack, onRestart }`.

Update the `Header` function signature and body:

```jsx
function Header({ nodeName, onBack, onRestart, noteHref, isGeneratingNote }) {
  return (
    <div className="flex items-center gap-3 px-6 py-3 border-b border-zinc-200 bg-white shrink-0">
      <button
        type="button"
        aria-label="返回图谱"
        onClick={onBack}
        className="p-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
      >
        <ArrowLeft className="w-4 h-4 text-zinc-600" />
      </button>
      <span className="font-semibold text-zinc-900 flex-1 truncate">{nodeName || '深入学习'}</span>
      {isGeneratingNote && (
        <span className="flex items-center gap-1.5 text-xs text-zinc-400 animate-pulse px-2 py-1.5">
          正在生成笔记...
        </span>
      )}
      {noteHref && !isGeneratingNote && (
        <a
          href={noteHref}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 px-3 py-1.5 rounded-lg transition-colors"
        >
          完成笔记 ↗
        </a>
      )}
      <button
        type="button"
        aria-label="重新开始"
        onClick={onRestart}
        disabled={!onRestart}
        className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-700 disabled:text-zinc-300 disabled:hover:bg-transparent px-2 py-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        重新开始
      </button>
    </div>
  );
}
```

**Change 3:** Pass the new props at both `Header` call sites inside `DeepLearnPage`.

Find the first `<Header` usage (inside the `!session` guard):
```jsx
        <Header
          nodeName={null}
          onBack={() => navigate(`/graph/${planId}`)}
          onRestart={null}
        />
```
Replace with:
```jsx
        <Header
          nodeName={null}
          onBack={() => navigate(`/graph/${planId}`)}
          onRestart={null}
          noteHref={null}
          isGeneratingNote={false}
        />
```

Find the second `<Header` usage (main render):
```jsx
      <Header
        nodeName={session.nodeName}
        onBack={() => navigate(`/graph/${planId}`)}
        onRestart={() => sendCommand('restart')}
      />
```
Replace with:
```jsx
      <Header
        nodeName={session.nodeName}
        onBack={() => navigate(`/graph/${planId}`)}
        onRestart={() => sendCommand('restart')}
        noteHref={noteId ? `/deep-learn/${planId}/${nodeId}/note/${noteId}` : null}
        isGeneratingNote={isGeneratingNote}
      />
```

**Acceptance criteria:**
- When `noteId` is null and `isGeneratingNote` is false: no note UI shown in header
- When `isGeneratingNote` is true: "正在生成笔记..." pulsing text shown, no note link
- When `noteId` is set: "完成笔记 ↗" link shown, opens in new tab at correct URL
- All existing Header behavior (back button, restart button) is unchanged

---

### F-03 — CompletionNotePage: zhihu-style note rendering

**File to create:** `frontend/src/pages/CompletionNotePage.jsx`

**Purpose:** Fetches the completion note by noteId, renders it in zhihu-style with wide margins, large typography, and a print button.

**Exact file content:**

```jsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer } from 'lucide-react';
import MarkdownContent from '../components/common/MarkdownContent';
import { buildApiUrl, tokenManager } from '../services/deepLearnApi';

export default function CompletionNotePage() {
  const { planId, nodeId, noteId } = useParams();
  const navigate = useNavigate();
  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchNote = async () => {
      try {
        const token = tokenManager?.get?.();
        const headers = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const res = await fetch(buildApiUrl(`/notes/${noteId}`), { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setNote(await res.json());
      } catch (e) {
        setError('无法加载笔记内容');
      } finally {
        setLoading(false);
      }
    };
    fetchNote();
  }, [noteId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-zinc-500 text-sm">
        加载笔记中...
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <p className="text-zinc-500 text-sm">{error || '笔记不存在'}</p>
        <button
          onClick={() => navigate(`/deep-learn/${planId}/${nodeId}`)}
          className="text-xs text-teal-600 hover:underline"
        >
          返回学习页
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Print-hidden controls */}
      <div className="print:hidden sticky top-0 z-10 bg-white border-b border-zinc-100 px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate(`/deep-learn/${planId}/${nodeId}`)}
          className="p-1.5 rounded-lg hover:bg-zinc-100 transition-colors"
          aria-label="返回"
        >
          <ArrowLeft className="w-4 h-4 text-zinc-600" />
        </button>
        <span className="text-sm text-zinc-500 flex-1">完成笔记</span>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-1.5 text-xs text-zinc-600 hover:text-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-200 hover:bg-zinc-50 transition-colors"
        >
          <Printer className="w-3.5 h-3.5" />
          导出 PDF
        </button>
      </div>

      {/* Note content — zhihu-style */}
      <article className="mx-auto max-w-2xl px-6 py-12 print:py-8 print:px-0 print:max-w-none">
        <div className="note-zhihu">
          <MarkdownContent content={note.content} />
        </div>
        <p className="mt-12 text-xs text-zinc-400 print:hidden">
          生成于 {new Date(note.created_at).toLocaleDateString('zh-CN')}
        </p>
      </article>
    </div>
  );
}
```

**Acceptance criteria:**
- Component renders without crash when `note` is null (shows error state)
- When note loads successfully, `MarkdownContent` receives `note.content`
- Printer icon and "导出 PDF" button are present and call `window.print()` on click
- Back button navigates to `/deep-learn/:planId/:nodeId`
- `print:hidden` class applied to controls so they don't appear in PDF

---

### F-04 — Print CSS for PDF export

**File to modify:** `frontend/src/index.css` (or equivalent global CSS entry point — look for `@tailwind base;` to confirm it's the right file)

**Purpose:** Add `@media print` rules so `window.print()` produces a clean PDF. Also add zhihu-style typography for the `.note-zhihu` class.

**Append at the end of the file:**

```css
/* ── Zhihu-style note typography ───────────────────────────── */
.note-zhihu {
  font-size: 16px;
  line-height: 1.8;
  color: #1a1a1a;
}

.note-zhihu h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  margin-top: 2rem;
}

.note-zhihu h2 {
  font-size: 1.375rem;
  font-weight: 600;
  margin-top: 2rem;
  margin-bottom: 0.5rem;
}

.note-zhihu p {
  margin-bottom: 1rem;
}

.note-zhihu blockquote {
  border-left: 3px solid #e5e7eb;
  padding-left: 1rem;
  color: #6b7280;
  margin: 1.25rem 0;
}

.note-zhihu code {
  background: #f4f4f5;
  padding: 0.15em 0.4em;
  border-radius: 4px;
  font-size: 0.875em;
}

.note-zhihu pre {
  background: #f4f4f5;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1.25rem 0;
}

/* ── Print / PDF export ─────────────────────────────────────── */
@media print {
  .print\:hidden {
    display: none !important;
  }

  body {
    font-size: 14px;
    background: white;
    color: black;
  }

  article {
    max-width: 100%;
    padding: 0;
  }

  a {
    color: inherit;
    text-decoration: none;
  }
}
```

**Acceptance criteria:**
- `.note-zhihu` styles apply to `CompletionNotePage` article content
- `@media print` block hides `.print:hidden` elements
- Existing styles in the file are not modified or removed
- `npm run build` succeeds with no CSS errors

---

### F-05 — App.jsx: add CompletionNotePage route

**File to modify:** `frontend/src/App.jsx`

**Change 1:** Add import at the top of the file (after existing page imports):

```jsx
import CompletionNotePage from './pages/CompletionNotePage';
```

**Change 2:** Add route inside `<Routes>`, after the existing `/deep-learn/:planId/:nodeId` route:

```jsx
                  <Route
                    path="/deep-learn/:planId/:nodeId/note/:noteId"
                    element={
                      <ProtectedRoute>
                        <CompletionNotePage />
                      </ProtectedRoute>
                    }
                  />
```

**Acceptance criteria:**
- Navigating to `/deep-learn/p1/n1/note/some-uuid` renders `CompletionNotePage` (not 404 redirect)
- Existing routes are unchanged
- `ProtectedRoute` wraps the page (unauthenticated users are redirected to `/auth`)

---

## INVARIANTS (do not violate)

1. **Note generation failure is non-fatal.** If `NoteGeneratorAgent.generate` raises or `save_completion_note` returns None, the session MUST still transition to COMPLETED and emit `node_completed`. The only difference: `note_ready` is omitted.
2. **GENERATING_NOTE must be in the DB constraint.** The `deep_learn_sessions.state` CHECK constraint must include `GENERATING_NOTE` before any code attempts to write it (B-01 must be executed in Supabase first).
3. **No new npm packages.** `window.print()` is built-in. `Printer` icon from `lucide-react`. No PDF libraries.
4. **`note_ready` carries only `note_id`.** Do not embed note content in the SSE event — content is fetched separately via `GET /notes/{note_id}`.
5. **User ownership check on note fetch.** `GET /notes/{note_id}` must verify `note["user_id"] == current_user_id` and return 403 otherwise.
6. **State order in `_run_final_judge`.** SSE emission order is mandatory: `state_change(→GENERATING_NOTE)` → `note_generating` → (generate + save) → `state_change(→COMPLETED)` → `note_ready` (if saved) → `node_completed`.
7. **`mark_node_learned` action is retired.** After B-06, `Decision.action` will never be `"mark_node_learned"` — do not add a fallback handler for it. Remove any dead-code branch if present.
8. **CompletionNotePage uses `buildApiUrl` from `deepLearnApi`.** Do not hardcode API base URL. Import from the existing `services/deepLearnApi.js` utility.

---

## MANUAL STEPS (not code — human must execute)

| Step | When | What |
|------|------|-------|
| M-01 | Before B-07 backend test | Execute `backend/sql/2026-05-21_completion_notes.sql` in Supabase SQL Editor |
| M-02 | After B-08 deployed | Smoke test: complete a full session, verify `note_ready` SSE fires and note is readable at `/api/deep-learn/notes/{note_id}` |
| M-03 | After F-05 deployed | Browser smoke test: navigate to note page, click "导出 PDF", verify controls are hidden in print preview |
