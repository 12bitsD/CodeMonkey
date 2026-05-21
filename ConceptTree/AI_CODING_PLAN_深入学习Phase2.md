# AI Coding Plan — 深入学习工作台 Phase 2

> 版本：v2.0（基于 PRD v0.3，承接 Phase 1 已实现的代码库）
> 适用：可被任何 AI coding agent 直接执行
> 设计原则：契约先行（Contract First）、原子任务、可验证、零隐式依赖

---

## 前提声明

本计划假定 Phase 1 已经实现并部署，具体包括：

```
backend/
├── models_deep_learn.py                                    [Phase 1 ✓]
├── services/deep_learn/
│   ├── session_repo.py / state_machine.py / service.py     [Phase 1 ✓]
│   └── agents/teaching.py / assessment_per_question.py / assessment_overall.py  [Phase 1 ✓]
├── routers/deep_learn.py                                   [Phase 1 ✓]

frontend/src/
├── services/deepLearnApi.js                                [Phase 1 ✓]
├── hooks/useDeepLearnSession.js                            [Phase 1 ✓]
├── pages/DeepLearnPage.jsx                                 [Phase 1 ✓]
└── components/deep-learn/                                  [Phase 1 ✓]
    ├── ConceptProgress.jsx / DeepLearnChat.jsx / CommandBar.jsx / MermaidDiagram.jsx
```

Phase 2 **只新增和修改**，不重写。任何对 Phase 1 文件的修改在任务里显式标记 `[MODIFY]`。

---

## Part 0 · Foundation（必读）

### 0.1 Phase 2 新增环境约定

| 约定 | 说明 |
|------|------|
| Supabase Storage | 用于存放 DALL-E 生成的图片。Bucket 名：`deep_learn_images`，public-read。需在 Supabase Dashboard 手动创建 bucket，设置 RLS 允许 authenticated user upload |
| Image API endpoint | OpenRouter 的 image 接口 `POST /api/v1/images/generations`，model `openai/gpt-image-2`。Auth 复用 `LLM_API_KEY`（OpenRouter key） |
| 图片缓存策略 | 不在 `deep_learn_sessions` 内冗余存图。图存 storage，URL 写入 SSE 流；前端如需"钉图"仅持 URL |
| 内存上下文长度 | Memory Context Block 严格限制 ≤ 800 字符。超出由 `MemoryContextBuilder` 截断 |
| 背景任务 | Memory Update 用 FastAPI `BackgroundTasks`（不要 spawn 裸 asyncio.create_task，会丢异常） |
| 度量单位 | Procedural Memory 聚合的"session 数"指 `learning_session_records.passed=TRUE OR passed=FALSE`（即完成的 session），不算 abandoned |
| 笔记复用 | 复用现有 `routers/notes.py` 的 `POST /api/notes/`，**不要**新建笔记 API |
| KaTeX | 用 `react-katex` 包，行内 `$x$` 和块级 `$$x$$` 语法。集成进 `MarkdownContent.jsx` 不影响其他页面 |

### 0.2 文件树增量

```
backend/
├── models_memory.py                                        [B-02] 新增
├── services/
│   ├── deep_learn/
│   │   ├── memory/
│   │   │   ├── __init__.py                                 [B-03]
│   │   │   ├── repository.py                               [B-03]
│   │   │   ├── context_builder.py                          [B-04]
│   │   │   ├── update_service.py                           [B-05]
│   │   │   └── update_agent.py                             [B-06]
│   │   ├── agents/
│   │   │   ├── image_trigger.py                            [B-07] 新增
│   │   │   └── teaching.py                                 [B-10] MODIFY
│   │   ├── image_storage.py                                [B-09] 新增
│   │   └── service.py                                      [B-11] MODIFY
│   └── llm/
│       ├── providers/
│       │   └── openai_compatible.py                        [B-08] MODIFY（加 generate_image）
│       └── configs/
│           ├── deep_learn_image_trigger.json               [B-07]
│           └── deep_learn_memory_update.json               [B-06]
└── routers/
    └── deep_learn.py                                       [B-12] MODIFY（仅加 pin/unpin endpoint）

frontend/src/
├── components/
│   ├── deep-learn/
│   │   ├── PinnedImages.jsx                                [F-03] 新增
│   │   ├── DalleImage.jsx                                  [F-04] 新增
│   │   ├── NotesButton.jsx                                 [F-06] 新增
│   │   ├── NotesModal.jsx                                  [F-06] 新增
│   │   ├── NotesSuggestionToast.jsx                        [F-07] 新增
│   │   ├── ConceptProgress.jsx                             [F-03] MODIFY（加 PinnedImages 区）
│   │   └── DeepLearnChat.jsx                               [F-04, F-05] MODIFY（图片消息渲染 + KaTeX）
│   └── common/
│       └── MarkdownContent.jsx                             [F-05] MODIFY（接 KaTeX）
├── hooks/
│   └── useDeepLearnSession.js                              [F-01, F-02] MODIFY（处理新事件 + 钉图状态）
├── services/
│   └── deepLearnApi.js                                     [F-06] MODIFY（加 pinImage / 笔记快捷调用）
└── pages/
    └── DeepLearnPage.jsx                                   [F-08] MODIFY（加 NotesButton/Modal mount）
```

### 0.3 类型契约（Single Source of Truth）

> 全部为新增类型；Phase 1 的契约保持不变。所有字段必须与此完全一致。

#### 0.3.1 Memory 数据模型

```python
# Long-term memory（独立表，PRD 中 user_learning_profile）
class LongTermMemory(BaseModel):
    user_id: str
    learning_style: dict        # {"analogy_type": "code"|"math"|"daily", "pace": "slow"|"normal"|"fast", "depth_preference": "concrete_first"|"abstract_first"}
    mastered_concepts: list[dict]  # [{"concept": str, "node_id": str, "mastered_at": isoformat str}]
    weak_concepts: list[dict]      # [{"concept": str, "node_id": str, "first_seen_at": isoformat str, "occurrences": int}]
    updated_at: str

# Episodic memory（一行 = 一次完成的 session）
class EpisodicRecord(BaseModel):
    id: str
    user_id: str
    node_id: str
    plan_id: str
    session_id: str
    summary: str                 # AI 生成，≤ 300 字
    concepts_covered: list[str]
    weak_points: list[str]
    strong_points: list[str]
    test_score: Optional[float]  # 0..1
    passed: bool
    conversation_turns: int
    created_at: str

# Procedural memory（一行 = 一个学习模式）
class ProceduralPattern(BaseModel):
    user_id: str
    pattern_key: str             # 取值见 §0.3.3
    pattern_value: str           # 自由文本
    confidence: float            # 0..1
    sample_count: int            # 该模式累计观察到的样本数
    updated_at: str
```

#### 0.3.2 Memory Context Block 契约

`MemoryContextBuilder.build(user_id, node_id, session) -> str` 返回如下纯文本（**不要 JSON**），用换行分隔：

```
[Memory Context]
长期记忆：{learning_style 摘要}。已掌握跨节点概念：{mastered_concepts 取最近 5 个}。
情节记忆：{该节点历史 session 摘要的最后一条，若无则 "首次学习此节点"}。
程序记忆：{procedural patterns 取 confidence>=0.6 的前 3 条}。
当前状态：本次进度 {current_concept_index+1}/{total}；已识别弱点：{weak_points 或 "无"}；难度 {difficulty_level}/5。
```

**约束**：
- 任何"找不到/为空"的字段用确定性占位文字（"无"/"首次学习此节点"），**禁止省略整行**
- 总长度 ≤ 800 字符，超出时优先丢弃 procedural 行
- 不允许出现 `None`、`null`、`undefined` 字面量

#### 0.3.3 Procedural Memory pattern_key 枚举

```python
ProceduralPatternKey = Literal[
    "effective_analogy_type",       # value: "code"|"math"|"daily"|"visual"
    "optimal_question_density",     # value: "1"|"2"|"3"  每概念建议题数
    "preferred_explanation_order",  # value: "concrete_first"|"abstract_first"
    "common_misconception_pattern", # value: 自由文本（描述常见误解类型）
    "ideal_pace",                   # value: "slow"|"normal"|"fast"
]
```

Memory Update Agent **只能**输出这 5 个 key，其他 key 静默丢弃。

#### 0.3.4 Image Trigger Agent 输出

```python
class ImageTriggerOutput(BaseModel):
    needs_image: bool
    image_type: Optional[Literal["mermaid", "dalle"]] = None
    mermaid_code: Optional[str] = None       # image_type == "mermaid" 时必填
    dalle_prompt: Optional[str] = None       # image_type == "dalle" 时必填，英文 prompt 效果更好
    reason: str                              # 给运维看的日志原因，不展示给用户
```

#### 0.3.5 Memory Update Event 契约

```python
class MemoryEvent(BaseModel):
    user_id: str
    session_id: str
    node_id: str
    event_type: Literal[
        "concept_passed",         # 用户通过某概念
        "concept_failed_twice",   # 连续答错触发
        "concept_skipped",
        "test_passed",
        "test_failed",
        "session_completed",      # session 状态变 completed 时触发（兜底）
    ]
    payload: dict                 # event 特定数据，如 {"concept": "...", "feedback": "..."}
```

### 0.4 SSE 事件目录（增量）

> Phase 1 已有的事件保持不变。Phase 2 **新增**以下事件：

```jsonc
// === DALL-E 图生成中（异步）===
// 先发 pending，DALL-E 调用完成后发 done。pending 立即发以便前端显示 loading
{"type": "image_dalle_pending", "id": "img-uuid", "reason": "为概念建立视觉直觉"}
{"type": "image_dalle_done", "id": "img-uuid", "url": "https://..."}

// === 笔记建议（AI 检测到关键定义） ===
{"type": "notes_suggestion", "snippet": "KV Cache 是把已经算过的 K/V 缓存起来，每次新生成 token 只需计算新的 Q 即可。"}
```

**对应 hook 处理**：

| 事件 | hook 状态变更 |
|------|--------------|
| `image_dalle_pending` | messages 追加 `{kind: 'dalle_pending', id, reason}` |
| `image_dalle_done` | 找到对应 `id` 的 message，把 kind 改为 `dalle_image`，content 设为 `url` |
| `notes_suggestion` | 设置 `noteSuggestion = event.snippet`，触发 toast 显示，5s 后自动消失或用户操作 |

### 0.5 Memory Update 触发表（Single Source of Truth）

> Service 层在状态机决策完成、**事件发生时**同步调用 `MemoryUpdateService.fire(event)`。该函数**仅做轻量记录或入队**；重的 LLM 调用通过 `BackgroundTasks` 异步执行。

| 触发场景 | event_type | 同步动作 | 异步动作 |
|---------|-----------|---------|---------|
| Assessment is_correct=True（单题/综合） | concept_passed | LongTerm.add_mastered(concept, node_id) | 无 |
| Assessment is_correct=False 且 wrong_count==2 | concept_failed_twice | LongTerm.upsert_weak(concept, node_id) | 无 |
| 状态机 mark_skipped 动作 | concept_skipped | 无（仅日志） | 无 |
| 测试通过（state=COMPLETED） | test_passed | Episodic.write_record(passed=True) + LongTerm.add_mastered for all done | 检查 user.completed_count，若是 5 的倍数 → 排队 Procedural 聚合 |
| 测试未通过（state=CHOOSING_AFTER_FAIL） | test_failed | Episodic.write_record(passed=False) | 同上 |
| Session status → completed/abandoned | session_completed | 兜底：若 episodic 未写则补写 | 同上 |

**关键约束**：
- 同步动作必须在 50ms 内完成（仅 DB 写）
- LLM 调用一律走 `BackgroundTasks`，不阻塞 SSE 流
- 任何 memory 写入失败必须 log error 但**不抛异常**给 Service 层（Memory 是增强，不应破坏教学主流程）

### 0.6 Image Generation 流程契约

```
TeachingAgent 输出 content（不再含 needs_image 字段，Phase 2 移交 ImageTrigger）
    │
    ▼
Service yield chunk events（content 流式输出完毕）
    │
    ▼
ImageTriggerAgent.decide(content, concept) → ImageTriggerOutput
    │
    ├── needs_image=False → 无事发生
    │
    ├── image_type="mermaid" → yield image_mermaid event（与 Phase 1 一致）
    │
    └── image_type="dalle" →
        1. 立即 yield image_dalle_pending event（前端显示 loading）
        2. 后台 await openai_provider.generate_image(prompt) → bytes
        3. upload_to_supabase_storage(bytes) → public URL
        4. yield image_dalle_done event with URL
```

**容错**：DALL-E 任何步骤失败 → 不阻塞、不重试，仅 log warning。前端 loading 卡片如 30s 内未收到 done，显示"图片生成失败"占位。

---

## Part 1 · Backend Tasks

### B-01：数据库扩展

**Goal**：在 Supabase SQL Editor 执行以下 DDL。Phase 2 不再修改 `deep_learn_sessions`。

```sql
-- Long-term Memory（独立表，避免与 user_profiles 冲突）
CREATE TABLE IF NOT EXISTS user_learning_profile (
  user_id           UUID PRIMARY KEY,
  learning_style    JSONB NOT NULL DEFAULT '{}'::jsonb,
  mastered_concepts JSONB NOT NULL DEFAULT '[]'::jsonb,
  weak_concepts     JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Episodic Memory
CREATE TABLE IF NOT EXISTS learning_session_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL,
  node_id             TEXT NOT NULL,
  plan_id             TEXT NOT NULL,
  session_id          UUID NOT NULL REFERENCES deep_learn_sessions(id) ON DELETE CASCADE,
  summary             TEXT,
  concepts_covered    JSONB NOT NULL DEFAULT '[]'::jsonb,
  weak_points         JSONB NOT NULL DEFAULT '[]'::jsonb,
  strong_points       JSONB NOT NULL DEFAULT '[]'::jsonb,
  test_score          REAL,
  passed              BOOLEAN NOT NULL DEFAULT FALSE,
  conversation_turns  INTEGER NOT NULL DEFAULT 0,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lsr_user_node_created
  ON learning_session_records(user_id, node_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lsr_user_passed
  ON learning_session_records(user_id, passed);

-- Procedural Memory
CREATE TABLE IF NOT EXISTS teaching_patterns (
  user_id       UUID NOT NULL,
  pattern_key   TEXT NOT NULL,
  pattern_value TEXT NOT NULL,
  confidence    REAL NOT NULL DEFAULT 0.5,
  sample_count  INTEGER NOT NULL DEFAULT 1,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, pattern_key),
  CONSTRAINT tp_pattern_key_check CHECK (pattern_key IN (
    'effective_analogy_type','optimal_question_density',
    'preferred_explanation_order','common_misconception_pattern','ideal_pace'
  ))
);
```

**Storage 配置（在 Supabase Dashboard）**：

1. 创建 Bucket：`deep_learn_images`，公开读
2. RLS Policy：
   ```sql
   -- 允许 authenticated 用户上传到自己 user_id 前缀的路径
   CREATE POLICY "users can upload own images" ON storage.objects
     FOR INSERT TO authenticated
     WITH CHECK (bucket_id = 'deep_learn_images' AND (storage.foldername(name))[1] = auth.uid()::text);
   ```

**Verify**：
- `SELECT * FROM user_learning_profile LIMIT 1;` 返回空但无错误
- `SELECT * FROM learning_session_records LIMIT 1;` 同上
- `SELECT * FROM teaching_patterns LIMIT 1;` 同上
- 在 Storage 上传一张测试图能返回 public URL

---

### B-02：Memory Pydantic Models

**File**：`backend/models_memory.py`

把 0.3.1 / 0.3.3 / 0.3.4 / 0.3.5 全部类型实现为 Pydantic 模型。

**必须导出**：
```
LongTermMemory, EpisodicRecord, ProceduralPattern,
ProceduralPatternKey,
ImageTriggerOutput,
MemoryEvent,
```

**Verify**：`python -c "from models_memory import LongTermMemory; print(LongTermMemory.model_fields.keys())"` 列出全部字段。

---

### B-03：Memory Repository

**File**：`backend/services/deep_learn/memory/repository.py`

**Goal**：封装三张表的 CRUD，**不含业务逻辑**。所有写入函数必须**捕获异常并 log，不抛出**（memory 写入失败不应破坏教学主流程）。

**导出函数签名**：

```python
# ── LongTerm ─────────────────────────────────────────────
def get_long_term(db: DbSession, user_id: str) -> Optional[LongTermMemory]: ...

def upsert_long_term_style(db: DbSession, user_id: str, style: dict) -> None:
    """部分覆盖 learning_style（merge 而非 replace）。
       SQL: INSERT ... ON CONFLICT (user_id) DO UPDATE SET learning_style = learning_style || ?::jsonb"""

def add_mastered_concept(db: DbSession, user_id: str, concept: str, node_id: str) -> None:
    """JSONB 数组 append，去重（同 concept+node_id 不重复加）"""

def upsert_weak_concept(db: DbSession, user_id: str, concept: str, node_id: str) -> None:
    """已存在 → occurrences+1；不存在 → 新增带 first_seen_at"""

# ── Episodic ─────────────────────────────────────────────
def write_episodic_record(db: DbSession, record: EpisodicRecord) -> str:
    """INSERT 返回 id。passed/failed 都写。"""

def get_recent_episodic_for_node(
    db: DbSession, user_id: str, node_id: str, limit: int = 1
) -> list[EpisodicRecord]:
    """按 created_at DESC 取最近 limit 条"""

def count_completed_sessions(db: DbSession, user_id: str) -> int:
    """SELECT COUNT(*) FROM learning_session_records WHERE user_id = ?"""

def get_all_episodic_since(db: DbSession, user_id: str, since_count: int) -> list[EpisodicRecord]:
    """取最近 since_count 条 episodic record，供 Procedural Memory 聚合用"""

# ── Procedural ───────────────────────────────────────────
def get_procedural_patterns(
    db: DbSession, user_id: str, min_confidence: float = 0.0
) -> list[ProceduralPattern]:
    """按 confidence DESC 排序"""

def upsert_procedural_pattern(
    db: DbSession, user_id: str, key: str, value: str, new_confidence: float
) -> None:
    """UPSERT。sample_count 自动 +1。pattern_key 不在白名单 → 静默丢弃 + log warning"""
```

**实现要点**：
- JSONB 数组的去重 append 用 PostgreSQL 表达式：
  ```sql
  UPDATE user_learning_profile
  SET mastered_concepts = (
    SELECT jsonb_agg(DISTINCT elem) FROM (
      SELECT jsonb_array_elements(mastered_concepts) AS elem
      UNION
      SELECT ?::jsonb
    ) t
  )
  WHERE user_id = ?
  ```
  或更简单：Python 端读出 list → 去重 → 整体覆盖（小数据集可接受，节点数 < 1000）
- 推荐用 Python 端方案，避免复杂 SQL

**Verify**：写临时脚本，依次：
- `add_mastered_concept(u, "A", "n1")` 两次 → 数组只含一个
- `upsert_weak_concept(u, "X", "n1")` 两次 → occurrences=2
- `count_completed_sessions(u)` 在写入 N 条后返回 N

---

### B-04：Memory Context Builder

**File**：`backend/services/deep_learn/memory/context_builder.py`

**Goal**：把三类持久 memory + 当前 session 拼成 §0.3.2 规定的纯文本块。

```python
class MemoryContextBuilder:
    MAX_LENGTH = 800

    def build(self, db: DbSession, user_id: str, node_id: str, session: SessionState) -> str:
        """返回 §0.3.2 格式的纯文本，长度 ≤ 800 字符"""
```

**实现步骤**：

1. 调 `repository.get_long_term(db, user_id)` 拿 long-term
2. 调 `repository.get_recent_episodic_for_node(db, user_id, node_id, limit=1)` 拿最近一次该节点的 session
3. 调 `repository.get_procedural_patterns(db, user_id, min_confidence=0.6)` 取前 3
4. 用 session 直接读出 `weak_points`、`difficulty_level`、`current_concept_index`、`what_list`
5. 严格按 §0.3.2 拼字符串
6. 长度超 800 → 优先丢 procedural 那行，仍超 → 截断长期记忆 mastered_concepts 列表
7. 任何 DB 异常 → 返回 fallback：`"[Memory Context]\n暂无历史记忆。当前进度 X/Y；当前难度 D/5。"`

**禁止**：在 builder 里调 LLM（这是纯字符串拼装）。

**Verify**：构造一个完整的 `SessionState` + 三张表的 mock 数据，调 build 后 `assert len(result) <= 800`，并人工读一遍格式是否符合 §0.3.2。

---

### B-05：Memory Update Service（事件分发）

**File**：`backend/services/deep_learn/memory/update_service.py`

**Goal**：实现 §0.5 触发表。Service 层在状态机决策完成时调用本服务的 `fire`。

```python
class MemoryUpdateService:
    def __init__(self): ...

    def fire(
        self,
        event: MemoryEvent,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> None:
        """同步处理 event，按 §0.5 表执行轻量动作。
           若需要 LLM 聚合（procedural），通过 background_tasks 排队。
        """
```

**实现分发逻辑**（精确对应 §0.5 表）：

```python
def fire(self, event, background_tasks=None):
    try:
        with get_db_context() as db:
            if event.event_type == "concept_passed":
                concept = event.payload["concept"]
                add_mastered_concept(db, event.user_id, concept, event.node_id)

            elif event.event_type == "concept_failed_twice":
                concept = event.payload["concept"]
                upsert_weak_concept(db, event.user_id, concept, event.node_id)

            elif event.event_type == "concept_skipped":
                logger.info("concept skipped: %s", event.payload.get("concept"))

            elif event.event_type in ("test_passed", "test_failed"):
                # 1) 写 episodic record（同步）
                record = self._build_episodic_record(db, event)
                write_episodic_record(db, record)
                # 2) 通过的话把所有 done concepts 写入 mastered
                if event.event_type == "test_passed":
                    for c in record.concepts_covered:
                        add_mastered_concept(db, event.user_id, c, event.node_id)
                # 3) 检查是否触发 procedural 聚合
                count = count_completed_sessions(db, event.user_id)
                if count % 5 == 0 and background_tasks is not None:
                    background_tasks.add_task(
                        self._run_procedural_aggregation, event.user_id, count
                    )

            elif event.event_type == "session_completed":
                # 兜底：检查是否已有 episodic record，若无则补一条
                if not has_episodic_record(db, event.session_id):
                    record = self._build_episodic_record(db, event)
                    write_episodic_record(db, record)
    except Exception as e:
        logger.error("MemoryUpdateService.fire failed: %s", e, exc_info=True)
        # 不抛出
```

**`_build_episodic_record`**：读 `deep_learn_sessions` 取 session，调 `MemoryUpdateAgent.summarize` 生成 summary（同步调用，因为这里就是 background context 或快速流程）。如果同步调 LLM 太慢，把 summarize 也丢给 background_tasks，先写一个空 summary 占位，summarize 完后 UPDATE。

**Verify**：单元测试模拟每种 event_type，验证 DB 操作和 background_tasks 入队符合 §0.5 表。

---

### B-06：Memory Update Agent

**File A**：`backend/services/llm/configs/deep_learn_memory_update.json`

```json
{
  "model_params": { "temperature": 0.4, "max_tokens": 1200 },
  "system_prompt": "你是学习记忆提炼专家。根据用户完成的 session 数据，提炼为以下两类输出，全部用中文：\n\n【场景 A · summarize（输入：一条 session 详情）】\n输出该 session 摘要：用户学了什么、卡在哪、整体掌握程度，≤ 300 字，紧凑、客观，不要赞美话术。\nJSON 格式：{\"summary\": \"...\"}\n\n【场景 B · aggregate_procedural（输入：最近 5 条 episodic 摘要）】\n从多个 session 中归纳该用户的稳定学习模式。输出 JSON：{\"patterns\": [{\"key\": \"effective_analogy_type\"|\"optimal_question_density\"|\"preferred_explanation_order\"|\"common_misconception_pattern\"|\"ideal_pace\", \"value\": \"...\", \"confidence\": 0.0-1.0}]}\n要求：\n- key 只能是上述 5 个值之一，其他静默丢弃\n- confidence 反映该模式在 5 条样本中的稳定性；样本中出现 ≥ 4/5 才给 ≥ 0.8\n- 每个 key 最多输出 1 条；总条数 0-5\n- value：effective_analogy_type ∈ {code,math,daily,visual}；optimal_question_density ∈ {1,2,3}；preferred_explanation_order ∈ {concrete_first,abstract_first}；ideal_pace ∈ {slow,normal,fast}；common_misconception_pattern 为自由文本一句话\n仅返回纯 JSON，不要 markdown 代码块包装。"
}
```

**File B**：`backend/services/deep_learn/memory/update_agent.py`

```python
class MemoryUpdateAgent:
    def __init__(self): ...

    async def summarize(
        self, *, session_data: dict, concepts_covered: list[str], test_results: list[dict],
    ) -> str:
        """场景 A：返回 ≤ 300 字 summary"""

    async def aggregate_procedural(
        self, *, recent_records: list[EpisodicRecord]
    ) -> list[ProceduralPattern]:
        """场景 B：返回 ProceduralPattern 列表（user_id/updated_at/sample_count 由调用方填）"""
```

**实现要点**：
- 加载 config 用 `json.load`，不要 `load_ai_config`
- `summarize` 失败兜底：返回 `"（自动摘要生成失败，请人工查看 conversation_history）"`
- `aggregate_procedural` 失败兜底：返回 `[]`
- pattern value 校验：不在白名单的 value 静默丢弃（除 `common_misconception_pattern`）

**Verify**：mock LLM 输出，分别测两种场景输出结构正确。

---

### B-07：Image Trigger Agent

**File A**：`backend/services/llm/configs/deep_learn_image_trigger.json`

```json
{
  "model_params": { "temperature": 0.3, "max_tokens": 600 },
  "system_prompt": "你是教学辅助图像决策器。根据 AI 家教刚讲完的内容，判断是否需要一张图来强化理解。\n\n【决策规则·分层】\n1. 内容有明确步骤顺序、流程或依赖关系 → image_type=mermaid，输出合法 mermaid graph LR/TD 代码\n2. 内容包含数学推导或公式 → 不需要图（KaTeX 由前端渲染），needs_image=false\n3. 内容描述复杂空间关系、架构图、Mermaid 难以表达 → image_type=dalle，输出简洁英文 prompt（≤ 100 token），明确风格 \"flat illustration, educational diagram\"\n4. 内容需要真实世界视觉类比（如\"想象一个图书馆\"） → image_type=dalle，prompt 描述该场景\n5. 其他纯文字概念 → needs_image=false\n\n【约束】\n- 同一概念已经讲过 N 次的话，不要重复出图\n- dalle 是付费资源，优先用 mermaid；只有 mermaid 表达力不够才用 dalle\n- mermaid_code 必须是合法语法（首行 graph LR 或 graph TD）\n\n仅返回纯 JSON：\n{\n  \"needs_image\": true,\n  \"image_type\": \"mermaid\" | \"dalle\" | null,\n  \"mermaid_code\": \"graph LR\\n  A-->B\" | null,\n  \"dalle_prompt\": \"...\" | null,\n  \"reason\": \"决策理由（运维日志用）\"\n}"
}
```

**File B**：`backend/services/deep_learn/agents/image_trigger.py`

```python
class ImageTriggerAgent:
    def __init__(self): ...

    async def decide(
        self, *,
        teaching_content: str,
        concept: str,
        node_name: str,
        previous_image_count: int = 0,   # 该 session 已生成的图片数，用于抑制过度生成
    ) -> ImageTriggerOutput: ...
```

**实现要点**：
- user_prompt 拼接：
  ```
  [节点] {node_name}
  [概念] {concept}
  [本 session 已生图次数] {previous_image_count}
  [刚讲完的内容]
  {teaching_content}

  请决策是否需要图，按系统 prompt 规则输出 JSON。
  ```
- 抑制策略：`previous_image_count >= 5` 时强制返回 `needs_image=False`，不调 LLM，省钱
- LLM 失败 → 返回 `needs_image=False`

**Verify**：mock 三种场景：步骤性内容 → mermaid；纯文字概念 → 不需图；空间关系 → dalle。

---

### B-08：扩展 LLM Provider 支持图像生成

**File**：`backend/services/llm/providers/openai_compatible.py` [MODIFY]

**Goal**：在 `OpenAICompatibleProvider` 类中加一个 `generate_image` 方法。

**新增方法签名**：

```python
async def generate_image(
    self,
    prompt: str,
    *,
    model: str = "openai/gpt-image-2",
    size: str = "1024x1024",
    quality: str = "standard",
) -> bytes:
    """调 OpenRouter 的 /api/v1/images/generations，返回 PNG bytes。
    
    用 self.client 已有的 AsyncOpenAI 实例。OpenRouter 兼容 OpenAI image API：
    
        response = await self.client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size=size,
            response_format="b64_json",
        )
        b64 = response.data[0].b64_json
        return base64.b64decode(b64)
    
    异常处理：捕获 APIError / APITimeoutError，raise LLMProviderError(...)
    """
```

**注意**：
- 不要新建 provider 类，复用现有
- 在 `services/llm/__init__.py` 不需要导出（只有 image_storage.py 调用它）
- 写入 unit test：mock `self.client.images.generate` 返回固定 b64，断言函数返回正确 bytes

**Verify**：以真实 OpenRouter key 跑一次集成测试（手动），返回 bytes 长度 > 1KB。

---

### B-09：Image Storage（Supabase Storage 上传）

**File**：`backend/services/deep_learn/image_storage.py`

**Goal**：上传 DALL-E 生成的 PNG 到 Supabase Storage，返回 public URL。

```python
async def upload_image(
    user_id: str,
    session_id: str,
    image_bytes: bytes,
    *,
    file_ext: str = "png",
) -> str:
    """上传到 Supabase Storage 的 deep_learn_images bucket。
    路径：{user_id}/{session_id}/{uuid4()}.{file_ext}
    返回：public URL (https://...supabase.co/storage/v1/object/public/deep_learn_images/...)
    """
```

**实现要点**：
- Supabase 的 storage API 通过 REST 调用：`POST {SUPABASE_URL}/storage/v1/object/{bucket}/{path}`
- Headers：`Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}`、`Content-Type: image/png`
- 从 `config.settings` 读取 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY`；如果这两个变量不存在，需在 `config.py` 加上（已有 `DATABASE_URL` 等，沿用 `Settings` 模式）
- 上传成功后 URL 拼接：`{SUPABASE_URL}/storage/v1/object/public/deep_learn_images/{path}`
- 用 `httpx.AsyncClient` 调用，timeout=30
- 失败 → raise `RuntimeError`，调用方负责 catch 并降级

**Verify**：手动上传一张测试图，浏览器打开返回的 URL 应能看到图。

---

### B-10：扩展 TeachingAgent 接受 Memory Context

**File**：`backend/services/deep_learn/agents/teaching.py` [MODIFY]

**修改内容**：

1. `TeachingAgent.run(...)` 新增可选参数：
   ```python
   async def run(
       self,
       *,
       node_name: str,
       node_why: str,
       current_concept: str,
       concept_index: int,
       total_concepts: int,
       difficulty_level: int,
       weak_points: list[str],
       recent_turns: list[dict],
       mode: TeachingMode,
       memory_context: str = "",   # 新增；Phase 1 调用方传空字符串，行为不变
   ) -> TeachingOutput: ...
   ```

2. user_prompt 拼接里**在 `[最近对话]` 之前**插入：
   ```
   {memory_context}

   ```
   如果 `memory_context` 为空字符串则跳过该段（保持 Phase 1 行为）。

3. 删除 `TeachingOutput.needs_image` / `mermaid_code` 的输出依赖逻辑：Phase 2 这些字段仍然存在于 schema（向前兼容），但 service.py 不再依赖 teaching 输出的图字段，改由 ImageTriggerAgent 决定。**不要删 Pydantic 模型字段**，避免破坏 Phase 1 的 fallback 逻辑。

**Verify**：传入非空 `memory_context`，检查 LLM prompt 中确实包含该字符串（可通过 mock client 抓取传入参数）。

---

### B-11：升级 Service 主流程

**File**：`backend/services/deep_learn/service.py` [MODIFY]

**修改总览**：

1. **构造函数**新增依赖：
   ```python
   self.memory_builder = MemoryContextBuilder()
   self.memory_updater = MemoryUpdateService()
   self.image_trigger = ImageTriggerAgent()
   ```

2. **每次调用 TeachingAgent.run 之前**：
   ```python
   with get_db_context() as db:
       memory_context = self.memory_builder.build(db, session.user_id, session.node_id, session)
   output = await self.teaching_agent.run(..., memory_context=memory_context)
   ```

3. **TeachingAgent.run 完成后**，**串行**追加 ImageTrigger 流程：
   ```python
   # （chunk 已发完）
   prev_img_count = sum(1 for m in session.recent_turns if m.get("kind") in ("mermaid","dalle_image"))
   trigger = await self.image_trigger.decide(
       teaching_content=output.content,
       concept=current_concept,
       node_name=node_meta["node_name"],
       previous_image_count=prev_img_count,
   )
   if trigger.needs_image:
       if trigger.image_type == "mermaid":
           yield _sse("image_mermaid", code=trigger.mermaid_code)
       elif trigger.image_type == "dalle":
           img_id = str(uuid4())
           yield _sse("image_dalle_pending", id=img_id, reason=trigger.reason)
           try:
               img_bytes = await llm_client.primary.generate_image(prompt=trigger.dalle_prompt)
               url = await image_storage.upload_image(session.user_id, session.id, img_bytes)
               yield _sse("image_dalle_done", id=img_id, url=url)
           except Exception as e:
               logger.warning("dalle generation failed: %s", e)
               yield _sse("image_dalle_done", id=img_id, url="")   # 空 URL → 前端显示失败占位
   ```

4. **每个 Memory Update 触发点**调用 `self.memory_updater.fire(MemoryEvent(...), background_tasks)`：

   | 触发位置 | event_type | payload |
   |---------|-----------|---------|
   | Assessment is_correct=True 后 | `concept_passed` | `{"concept": current_concept_name}` |
   | wrong_count == 2 时 | `concept_failed_twice` | `{"concept": current_concept_name}` |
   | mark_skipped 时 | `concept_skipped` | `{"concept": skipped_concept_name}` |
   | 测试通过分支 | `test_passed` | `{"concepts_covered": [...], "weak_points": [...], "test_results": [...]}` |
   | 测试未通过分支 | `test_failed` | `{"concepts_covered": [...], "weak_points": [...]}` |

5. **如何把 `BackgroundTasks` 传到 service**：router 层修改 endpoint 签名增加 `background_tasks: BackgroundTasks`，调用 `service.stream_message(...)` 时通过参数传入。Service 层的 `stream_message/stream_command/stream_initialize` 都增加 `background_tasks` 参数。

**Verify**：
- 端到端跑一次完整 happy path，检查：
  - LLM 调用日志能看到 prompt 里有 Memory Context Block
  - 测试通过后 `learning_session_records` 表多了一条记录
  - `user_learning_profile.mastered_concepts` 数组包含已通过的概念
  - 至少一个概念触发了 mermaid 或 dalle 输出

---

### B-12：Router 修改 + 笔记 SSE 集成

**File**：`backend/routers/deep_learn.py` [MODIFY]

**修改**：

1. 三个 SSE endpoint（initialize / message / command）参数加上 `background_tasks: BackgroundTasks = BackgroundTasks()`，传给 service
2. （可选）新增 `POST /api/deep-learn/sessions/{session_id}/note-suggestions/{snippet_id}/dismiss` — 接收前端关闭建议的回执，**Phase 2 可以不做**，等用户反馈再加

**关于笔记建议**：
- 不新增 endpoint。`notes_suggestion` SSE 事件由 TeachingAgent 输出后由 Service 决定何时发：
- 简化策略：Service 检测到 `output.content` 中含"是"/"=="/"指的是"等定义性词汇 + 段落首句（即解释段第一句）→ 发 `notes_suggestion`，snippet 取该段第一句
- 前端拿到 snippet 调现有 `POST /api/notes/` 创建笔记
- 这一行为放在 service.py 里实现，加一个辅助函数 `_maybe_emit_note_suggestion(content) -> Optional[str]`，规则简单到不需要 LLM

**Verify**：跑一次完整 session，至少一次 chunk 后伴随 `notes_suggestion` 事件。

---

## Part 2 · Frontend Tasks

### F-01：Hook 接收新 SSE 事件

**File**：`frontend/src/hooks/useDeepLearnSession.js` [MODIFY]

**新增状态**：
```javascript
const [pinnedImages, setPinnedImages] = useState([]);  // [{id, url, caption}]
const [noteSuggestion, setNoteSuggestion] = useState(null);  // {snippet, timestamp}
```

**新增事件处理**（在原 switch/if-else 中追加分支）：

```javascript
case 'image_dalle_pending':
  setMessages(prev => [...prev, { role: 'assistant', kind: 'dalle_pending', id: event.id, reason: event.reason }]);
  break;

case 'image_dalle_done':
  setMessages(prev => prev.map(m =>
    m.kind === 'dalle_pending' && m.id === event.id
      ? { ...m, kind: 'dalle_image', content: event.url }
      : m
  ));
  break;

case 'notes_suggestion':
  setNoteSuggestion({ snippet: event.snippet, timestamp: Date.now() });
  // 5s 后自动清空
  setTimeout(() => setNoteSuggestion(curr => curr?.timestamp === Date.now() ? null : curr), 5000);
  break;
```

**新增导出 API**：
```javascript
return {
  ...existingState,
  pinnedImages,
  pinImage: (id, url, caption) => setPinnedImages(prev =>
    prev.find(p => p.id === id) ? prev : [...prev, { id, url, caption }]
  ),
  unpinImage: (id) => setPinnedImages(prev => prev.filter(p => p.id !== id)),
  noteSuggestion,
  dismissNoteSuggestion: () => setNoteSuggestion(null),
};
```

**约束**：
- 钉图状态**仅 session 内有效**，刷新页面丢失（Phase 2 不持久化）
- DALL-E pending 卡片 30 秒后无 done 事件则前端自行变 dalle_image content="" 显示失败占位

**Verify**：mock 两条 SSE 序列（pending → done；pending → 永远不来），UI 表现正确。

---

### F-02：API Service 扩展（笔记快捷调用）

**File**：`frontend/src/services/deepLearnApi.js` [MODIFY]

新增：
```javascript
import { tokenManager } from './api';
import { buildApiUrl } from '../config/api';

// 复用现有笔记 API，封装为一行调用
export const createNoteFromDeepLearn = async ({ planId, nodeId, content }) => {
  const res = await fetch(buildApiUrl('/api/notes/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokenManager.get()}` },
    body: JSON.stringify({ planId, nodeId, content }),
  });
  if (!res.ok) throw new Error('create note failed');
  return res.json();
};
```

**Verify**：从 console 调用一次，能在数据库 `notes` 表看到新行。

---

### F-03：PinnedImages 组件 + ConceptProgress 集成

**File A**：`frontend/src/components/deep-learn/PinnedImages.jsx`

```jsx
import { X } from 'lucide-react';

export default function PinnedImages({ pinned = [], onUnpin }) {
  if (pinned.length === 0) return null;
  return (
    <div className="px-4 pb-4 space-y-3 border-t border-zinc-100 pt-3">
      <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">钉图区</p>
      {pinned.map(img => (
        <div key={img.id} className="relative bg-zinc-50 rounded-xl overflow-hidden border border-zinc-200">
          {img.url ? (
            <img src={img.url} alt={img.caption || ''} className="w-full" />
          ) : (
            <div className="p-6 text-center text-zinc-400 text-sm">图片加载失败</div>
          )}
          <button
            onClick={() => onUnpin(img.id)}
            className="absolute top-1.5 right-1.5 p-1 rounded-full bg-white/80 hover:bg-white shadow"
          >
            <X size={14} />
          </button>
          {img.caption && <p className="px-3 py-2 text-xs text-zinc-500">{img.caption}</p>}
        </div>
      ))}
    </div>
  );
}
```

**File B**：`frontend/src/components/deep-learn/ConceptProgress.jsx` [MODIFY]

在原组件末尾（弱点追踪之后）追加：
```jsx
<PinnedImages pinned={pinnedImages} onUnpin={onUnpinImage} />
```

ConceptProgress 的 props 新增 `pinnedImages`、`onUnpinImage` 两个。

**Verify**：钉一张图，左侧出现；点 X 消失。

---

### F-04：DalleImage 组件 + Chat 集成

**File A**：`frontend/src/components/deep-learn/DalleImage.jsx`

```jsx
import { Pin } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function DalleImage({ id, url, reason, onPin, pending = false }) {
  const [timeout30s, setTimeout30s] = useState(false);
  useEffect(() => {
    if (pending) {
      const t = setTimeout(() => setTimeout30s(true), 30000);
      return () => clearTimeout(t);
    }
  }, [pending]);

  if (pending && !url) {
    return (
      <div className="my-3 p-6 bg-zinc-50 rounded-xl border border-dashed border-zinc-300 text-center text-sm text-zinc-500">
        {timeout30s ? '图片生成失败' : '正在生成图片...'}
      </div>
    );
  }
  if (!url) {
    return <div className="my-3 p-6 bg-zinc-50 rounded-xl border border-zinc-200 text-center text-sm text-zinc-400">图片不可用</div>;
  }
  return (
    <div className="my-3 group relative inline-block max-w-full">
      <img src={url} alt={reason || ''} className="rounded-xl border border-zinc-200 max-w-full" />
      <button
        onClick={() => onPin?.(id, url, reason)}
        className="absolute top-2 right-2 p-1.5 rounded-full bg-white/90 hover:bg-white shadow opacity-0 group-hover:opacity-100 transition-opacity"
        title="钉到左侧"
      >
        <Pin size={14} />
      </button>
    </div>
  );
}
```

**File B**：`frontend/src/components/deep-learn/DeepLearnChat.jsx` [MODIFY]

在消息渲染 switch 里加：
```jsx
} else if (msg.kind === 'dalle_pending' || msg.kind === 'dalle_image') {
  return (
    <div className="max-w-[85%]">
      <DalleImage
        id={msg.id}
        url={msg.kind === 'dalle_image' ? msg.content : null}
        reason={msg.reason}
        pending={msg.kind === 'dalle_pending'}
        onPin={onPinImage}
      />
    </div>
  );
}
```

`DeepLearnChat` 的 props 新增 `onPinImage`。Mermaid 消息也加 Pin 按钮（在 MermaidDiagram 外层包一个 group + Pin button，复制 DalleImage 的逻辑），让 Mermaid 也能钉到左侧（用 SVG 截图 → 转 base64 dataURL 钉过去，或更简单：把 mermaid_code 钉过去，左侧也用 MermaidDiagram 渲染）。

**推荐做法**：钉 mermaid 时把 `code` 作为"url"传入（一个特殊标志），PinnedImages 检测到 url 以 `mermaid:` 开头就用 MermaidDiagram 渲染。简单点：`pinImage(id, 'mermaid:' + code, caption)`，PinnedImages 用条件渲染分发。

**Verify**：DALL-E pending → loading 卡片；done → 真图 + 钉图按钮。Mermaid 也可钉。

---

### F-05：KaTeX 集成

**安装**：`cd frontend && npm install katex react-katex`

**File**：`frontend/src/components/common/MarkdownContent.jsx` [MODIFY]

加入 KaTeX 支持。如果当前用的是 `react-markdown` 或类似库，加 `remark-math` + `rehype-katex` plugin：

```bash
npm install remark-math rehype-katex katex
```

```jsx
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';   // 全局 CSS（只导入一次）

// 在 ReactMarkdown 配置里加：
<ReactMarkdown
  remarkPlugins={[remarkGfm, remarkMath]}
  rehypePlugins={[rehypeKatex]}
  ...
/>
```

**约束**：
- KaTeX 的 CSS 仅在 MarkdownContent 模块导入一次，避免多页面重复加载
- 测试 `$x^2$` 行内、`$$\sum_{i=1}^n x_i$$` 块级两种语法都渲染正确
- 如果当前 `MarkdownContent.jsx` 不是用 react-markdown，需要分析当前实现并平滑集成；不要重写整个组件

**Verify**：在 DeepLearnChat 测试一段含数学公式的 AI 输出，正确渲染。

---

### F-06：Notes Modal

**File A**：`frontend/src/components/deep-learn/NotesButton.jsx`

```jsx
import { NotebookPen } from 'lucide-react';

export default function NotesButton({ onClick, hasUnsaved = false }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 transition-colors w-full"
    >
      <NotebookPen size={16} />
      <span>笔记</span>
      {hasUnsaved && <span className="ml-auto w-2 h-2 rounded-full bg-amber-500"/>}
    </button>
  );
}
```

**File B**：`frontend/src/components/deep-learn/NotesModal.jsx`

```jsx
import { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import MarkdownContent from '../common/MarkdownContent';
import { createNoteFromDeepLearn } from '../../services/deepLearnApi';

export default function NotesModal({ open, onClose, planId, nodeId, initialContent = '' }) {
  const [content, setContent] = useState(initialContent);
  const [saving, setSaving] = useState(false);
  const [savedToast, setSavedToast] = useState(false);

  useEffect(() => {
    if (open) setContent(initialContent);
  }, [open, initialContent]);

  if (!open) return null;

  const handleSave = async () => {
    if (!content.trim()) return;
    setSaving(true);
    try {
      await createNoteFromDeepLearn({ planId, nodeId, content });
      setSavedToast(true);
      setTimeout(() => { setSavedToast(false); onClose(); }, 800);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-4xl h-[80vh] flex flex-col shadow-2xl" onClick={e => e.stopPropagation()}>
        <header className="flex items-center justify-between p-4 border-b border-zinc-200">
          <h3 className="font-medium">笔记</h3>
          <button onClick={onClose}><X size={18}/></button>
        </header>
        <div className="flex-1 flex overflow-hidden">
          <textarea
            className="flex-1 p-4 resize-none outline-none border-r border-zinc-100 text-sm font-mono"
            value={content}
            onChange={e => setContent(e.target.value)}
            placeholder="支持 Markdown 语法..."
          />
          <div className="flex-1 p-4 overflow-y-auto bg-zinc-50">
            <MarkdownContent content={content || '_预览区_'} />
          </div>
        </div>
        <footer className="p-4 border-t border-zinc-200 flex justify-end gap-2">
          {savedToast && <span className="text-sm text-emerald-600 self-center">已保存 ✓</span>}
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg border border-zinc-200 text-sm">取消</button>
          <button onClick={handleSave} disabled={saving || !content.trim()} className="px-3 py-1.5 rounded-lg bg-zinc-800 text-white text-sm flex items-center gap-1.5 disabled:opacity-40">
            <Save size={14}/> 保存
          </button>
        </footer>
      </div>
    </div>
  );
}
```

**Verify**：打开 modal，输入内容，左右两边同步；点保存，数据库 `notes` 表新增一行。

---

### F-07：NotesSuggestionToast

**File**：`frontend/src/components/deep-learn/NotesSuggestionToast.jsx`

```jsx
import { NotebookPen, X } from 'lucide-react';

export default function NotesSuggestionToast({ suggestion, onAdd, onDismiss }) {
  if (!suggestion) return null;
  return (
    <div className="fixed bottom-6 right-6 z-40 max-w-md bg-white rounded-2xl shadow-2xl border border-amber-200 p-4 animate-slide-up">
      <div className="flex items-start gap-3">
        <NotebookPen size={18} className="text-amber-600 mt-0.5 shrink-0"/>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-zinc-500 mb-1">加入笔记？</p>
          <p className="text-sm text-zinc-800 truncate">{suggestion.snippet}</p>
        </div>
        <button onClick={onDismiss}><X size={14}/></button>
      </div>
      <div className="flex gap-2 mt-3 justify-end">
        <button onClick={onDismiss} className="px-3 py-1 text-xs rounded-lg text-zinc-500 hover:bg-zinc-100">忽略</button>
        <button onClick={() => onAdd(suggestion.snippet)} className="px-3 py-1 text-xs rounded-lg bg-amber-500 text-white">加入</button>
      </div>
    </div>
  );
}
```

`onAdd` 应该打开 NotesModal 并把 snippet 作为 `initialContent` 传入。

---

### F-08：DeepLearnPage 集成

**File**：`frontend/src/pages/DeepLearnPage.jsx` [MODIFY]

修改要点：

1. 解构 hook 时取出新的状态：
   ```js
   const {
     ..., pinnedImages, pinImage, unpinImage,
     noteSuggestion, dismissNoteSuggestion,
   } = useDeepLearnSession({ planId, nodeId });
   ```

2. State：`const [notesOpen, setNotesOpen] = useState(false);`、`const [notesInitial, setNotesInitial] = useState('');`

3. ConceptProgress 传入 `pinnedImages={pinnedImages}`、`onUnpinImage={unpinImage}`

4. ConceptProgress 下方追加 `<NotesButton onClick={() => { setNotesInitial(''); setNotesOpen(true); }} />`

5. DeepLearnChat 传入 `onPinImage={pinImage}`

6. 页面底部挂载：
   ```jsx
   <NotesModal
     open={notesOpen}
     onClose={() => setNotesOpen(false)}
     planId={planId}
     nodeId={nodeId}
     initialContent={notesInitial}
   />
   <NotesSuggestionToast
     suggestion={noteSuggestion}
     onAdd={(snippet) => { setNotesInitial(snippet); setNotesOpen(true); dismissNoteSuggestion(); }}
     onDismiss={dismissNoteSuggestion}
   />
   ```

**Verify**：手工跑全流程，NotesButton 可打开 modal，AI 解释后出现 toast。

---

## Part 3 · Smoke Tests

T-01 ~ T-05 沿用 Phase 1（确保不回归）。新增 T-06 ~ T-12：

### T-06：Long-term Memory 写入

1. 完整跑通一次"通过测试"流程
2. 检查 `SELECT mastered_concepts FROM user_learning_profile WHERE user_id = ?`
3. 期望：包含本次 session 所有 `done` 概念

### T-07：Episodic Memory 写入

1. 完成一次测试通过 + 一次测试未通过
2. 检查 `SELECT * FROM learning_session_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 2`
3. 期望：两条记录，passed 分别为 true/false，summary 非空

### T-08：Procedural Memory 聚合触发

1. 完成 5 次 session（可以同一节点反复重启）
2. 等 1-2 分钟（BackgroundTasks 完成）
3. 检查 `SELECT * FROM teaching_patterns WHERE user_id = ?`
4. 期望：1-5 条 pattern 记录，confidence 在 0-1 之间

### T-09：Memory Context Block 注入

1. 给用户预先插一条 episodic record（模拟历史）
2. 启动一个新 session，开启 backend log
3. 查 LLM 请求日志的 user_prompt 字段
4. 期望：包含 `[Memory Context]` 标签和上次卡住的描述

### T-10：DALL-E 图生成

1. 让 AI 讲一个明显需要架构图的概念（如"Transformer 编码器结构"）
2. 期望：先看到 loading 卡片，约 5-15s 后变成真图
3. 点 Pin → 左侧出现，点 X → 消失

### T-11：KaTeX 渲染

1. 让 AI 讲一个含数学公式的概念（如"反向传播链式法则"）
2. 期望：行内 $x$ 和块级 $$\frac{\partial L}{\partial w}$$ 都正确渲染

### T-12：Notes 完整流程

1. AI 讲完一段，看到 NotesSuggestionToast 弹出
2. 点"加入" → NotesModal 打开，initialContent 是 snippet
3. 编辑后保存 → toast 提示已保存
4. 数据库 `notes` 表新增一行，content 字段匹配

---

## Part 4 · Anti-patterns（禁止）

| 反模式 | 正确做法 |
|--------|---------|
| Memory 写失败时抛异常给 service.py | 全部 try/except + log，不抛出 |
| 在 SSE generator 内部同步调 DALL-E（5-15s 阻塞） | 把生成移到 generator 内异步 await，先发 pending 占位 |
| 把图片 base64 直接塞进 SSE chunk | DALL-E 图必走 Storage 上传，SSE 只传 URL |
| Memory Context Block 用 JSON 格式塞进 prompt | 用自然语言纯文本（LLM 对自然语言更敏感） |
| Procedural Memory 每个 session 都触发 LLM 聚合 | 必须按 5 的倍数触发，省钱 |
| 在前端 hook 里把 pinnedImages 持久化到 localStorage | Phase 2 不持久化，刷新即消失 |
| KaTeX 在 ChatMarkdownMessage 单独再加一遍渲染逻辑 | 只在 MarkdownContent 加一次，复用 |
| 新建 notes API endpoint | 复用现有 `POST /api/notes/`，零侵入 |
| 用 `BackgroundTasks` 跑超过 30s 的任务 | FastAPI BG 不适合长任务；如未来超时严重，迁移到外部队列。Phase 2 的聚合 ≤ 30s 可接受 |
| Image Trigger Agent 对每段内容都调 LLM | 加 `previous_image_count >= 5` 短路 |
| 在 `user_profiles` 表直接加列 | 用独立 `user_learning_profile` 表，避免影响现有 user 流程 |
| Memory Context 拼接遇到 None 时塞 `"None"` 字符串 | 必须用确定性占位文字（"无"/"首次..."），不允许 `None` 字面量 |

---

## 执行顺序建议

**第 1 天**：B-01（DDL + Storage 配置）→ B-02 → B-03 + 临时验证脚本
**第 2 天**：B-04（builder）→ B-05（update service）→ B-06（agent）
**第 3 天**：B-07（image trigger）→ B-08（provider 扩展）→ B-09（storage）
**第 4 天**：B-10 → B-11（service 整合，**最难的一步**）→ B-12 → 后端端到端 smoke
**第 5 天**：F-01 → F-02 → F-03（Pinned）→ F-04（Dalle in Chat）
**第 6 天**：F-05（KaTeX）→ F-06（Notes Modal）→ F-07（Toast）→ F-08（Page 整合）
**第 7 天**：T-06 ~ T-12 全跑通 + fix bug

---

## 完成定义（Phase 2 Done）

- [ ] Phase 1 的 T-01 ~ T-05 全部不回归
- [ ] T-06 ~ T-12 全部手动验证通过
- [ ] `learning_session_records` 表有有效数据，`summary` 字段非空
- [ ] `user_learning_profile.mastered_concepts` 与实际通过的概念一致
- [ ] 至少 1 次 session 触发了 DALL-E 图生成且成功 upload
- [ ] 完成 5 个 session 后，`teaching_patterns` 表有 ≥ 1 条记录
- [ ] 浏览器 console 完整流程零 error
- [ ] 数学公式（KaTeX）和 Mermaid 都能正确渲染
- [ ] 笔记 modal 创建的笔记在节点详情页可见

---

## 已知限制 / Phase 3 处理

- 钉图状态不持久化（刷新丢失） — Phase 3 再考虑是否持久化
- DALL-E 失败无重试 — 一次失败即放弃，避免成本失控
- Procedural Memory 不支持"过期"（旧 pattern 永远存在） — Phase 3 引入 TTL 或 sample_count 衰减
- Memory Context Block 是简单字符串拼接，没有相关性 ranking — Phase 3 引入 embedding 检索
- 笔记建议规则极简（关键词匹配） — Phase 3 用 LLM 做更智能的"关键定义"检测
