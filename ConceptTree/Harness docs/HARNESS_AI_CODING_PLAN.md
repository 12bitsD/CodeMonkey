# AI Coding Plan — ConceptTree Multi-Agent Graph Generation v2

> Source of truth: PRD_MultiAgent_v2.md  
> Codebase root: `backend/` and `frontend/src/`  
> Execution order: Tasks are labeled B1–B6 (backend) and F1–F5 (frontend).  
> Dependencies are explicit. Do not begin a task until all its dependencies are complete.

---

## CONTEXT SNAPSHOT

### Current generate-graph flow (v1, DO NOT MODIFY until B6)

```
POST /api/ai/generate-graph
  → ai_service.generate_graph()          # single LLM call, 4096 tokens
  → _stream_graph_nodes() in routers/ai.py
  → SSE events: meta | node | edges | done
```

### Target generate-graph flow (v2, NEW)

```
POST /api/ai/generate-graph-v2
  → ai_service.generate_graph_v2_stream()
      → _run_phase1()                    # Curriculum Architect, max_tokens=2000
      yield SSE: skeleton
      → asyncio.gather(_run_phase2_node × N, semaphore=8)
      yield SSE: node_ready  (×N, as each completes)
      → _run_phase3()                    # Integration Agent, max_tokens=3000
      yield SSE: integration_done
      yield SSE: done
```

### Key existing patterns to follow

- Config loading: `load_ai_config(name, user_input, **kwargs)` in `services/llm/configs/__init__.py`
  - `{{key}}` in `system_prompt` → replaced by kwargs
  - kwargs NOT in system_prompt → appended to user_prompt
- LLM JSON call: `self.llm_client.chat_json(system_prompt, user_prompt, temperature, max_tokens, model)`
- SSE format: `f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"`
- Pydantic models live in `models.py`; AI result wrappers follow `XXXAIResult(success, data, error)` pattern
- StreamingResponse in routers uses `AsyncGenerator[str, None]`

---

## TASK DEPENDENCY GRAPH

```
B1 ──┐
B2 ──┼──► B5 ──► B6
B3 ──┘         
B4 ────────► B5

F1 ──────────────────────────────────► F5
F2 ──────────────────────────────────► F5
F3 ──────────────────────────────────► F5
F4 ──────────────────────────────────► F5
```

---

## BACKEND TASKS

---

### B1 — Create `curriculum_architect.json`

**File to create:** `backend/services/llm/configs/curriculum_architect.json`

**Purpose:** Phase 1 prompt config. Outputs graph skeleton only — no coordinates, no content fields.

**Exact file content:**

```json
{
  "model_params": {
    "temperature": 0.5,
    "max_tokens": 2000
  },
  "system_prompt": "You are a curriculum architect. Your job is to design the skeleton of a knowledge dependency graph for a learning goal. The user's learning purpose is: {{learning_purpose}}.\n\nLearning purpose definitions:\n- explore: lightweight overview, fewer nodes\n- apply: practical depth, moderate nodes\n- master: comprehensive, more nodes\n\nDo NOT generate content (why/what/mastery/resources). Only generate structure.",
  "output_format": {
    "nodes": [
      {
        "id": "n1",
        "name": "节点名（中文）",
        "domain": "语义领域标签（中文，如：数学基础 / 编程实现 / 核心理论）"
      }
    ],
    "edges": [
      {"from_node": "n1", "to_node": "n2"}
    ],
    "targetNodeId": "n2"
  },
  "rules": [
    "Node count: You decide. Simple skill → ~5 nodes. Deep domain → 15-20+ nodes. Do not pad. Do not truncate. Base on actual topic complexity and learning_purpose.",
    "id: Must follow n1, n2, n3 format sequentially.",
    "name: Must be Chinese.",
    "domain: Assign a short Chinese semantic tag (2-6 chars). Nodes covering related concepts should share the same domain. Aim for 2-5 distinct domains per graph.",
    "edges: from_node is the prerequisite. to_node depends on from_node. No circular dependencies. targetNodeId must have at least 2 incoming edges.",
    "targetNodeId: Exactly one node is the learning target. It should be in the most central position of the dependency chain.",
    "Do NOT output: x, y, why, what, mastery, prompt, resources, phase, phase_order, depth_level."
  ],
  "examples": [
    {
      "input": "理解反向传播的数学原理 (learning_purpose=apply)",
      "output": "nodes: [{id:n1,name:导数基础,domain:数学基础},{id:n2,name:偏导数,domain:数学基础},{id:n3,name:链式法则,domain:数学基础},{id:n4,name:矩阵运算,domain:线性代数},{id:n5,name:梯度下降,domain:核心算法},{id:n6,name:反向传播,domain:核心算法},{id:n7,name:梯度调试,domain:工程实践},{id:n8,name:实现一个MLP,domain:工程实践}], targetNodeId:n6, edges:[n1→n3,n2→n3,n3→n5,n4→n5,n5→n6,n6→n7,n6→n8]"
    }
  ]
}
```

**Acceptance criteria:**
- File is valid JSON parseable by `json.load()`
- `load_ai_config("curriculum_architect", "some goal", learning_purpose="apply")` returns without error
- `{{learning_purpose}}` placeholder is present in `system_prompt`

---

### B2 — Create `content_generator.json`

**File to create:** `backend/services/llm/configs/content_generator.json`

**Purpose:** Phase 2 prompt config. Called once per node. Generates rich content for a single node.

**Exact file content:**

```json
{
  "model_params": {
    "temperature": 0.7,
    "max_tokens": 1500
  },
  "system_prompt": "You are an expert learning content designer. Generate rich, specific learning content for a single knowledge node in a larger learning graph.\n\nOverall learning goal: {{learning_goal}}\nLearning purpose: {{learning_purpose}}\n\nYour output must be for this specific node only. Do not describe the whole graph.",
  "output_format": {
    "node_id": "n1",
    "why": "2-3 sentences explaining WHY this node matters for the overall learning goal. Be specific about the connection.",
    "what": [
      "Specific subtopic or concept the learner must understand (use Chinese)",
      "Another specific subtopic"
    ],
    "mastery": [
      "Actionable, verifiable mastery check — what can the learner DO or EXPLAIN (use Chinese)"
    ],
    "prompt": "A specific question the learner can ask an AI tutor to go deeper on this node (Chinese)",
    "resources": [
      {"name": "Resource name", "url": "", "reason": "Why this resource fits this node"}
    ]
  },
  "rules": [
    "node_id: Echo back the exact node_id provided in the input.",
    "why: Connect directly to the overall learning_goal. Be specific. Do not write generic motivation.",
    "what: List ALL distinct subtopics the learner must cover. No fixed count. Simple nodes: 3-4 items. Core algorithm/theory nodes: 5-8 items. Tool/practice nodes: 3-6 items. Each item should be a concrete, learnable unit.",
    "Avoid overlap: The input includes neighbor_names (other nodes in the graph). Do NOT repeat concepts already fully covered by a neighbor node.",
    "Build on prerequisites: The input includes prerequisite_names. Your content should assume those are already known and build upward.",
    "mastery: Must be actionable checks (e.g. '能用代码实现X', '能解释为什么Y'). Not abstract descriptions.",
    "resources: 1-3 resources. Leave url empty if uncertain. Do not fabricate URLs.",
    "Output language: Chinese for why/what/mastery/prompt. Resource names can be English."
  ]
}
```

**Acceptance criteria:**
- File is valid JSON
- `load_ai_config("content_generator", "node_name", learning_goal="X", learning_purpose="apply", neighbor_names="A,B", prerequisite_names="C")` returns without error

---

### B3 — Create `integration_agent.json`

**File to create:** `backend/services/llm/configs/integration_agent.json`

**Purpose:** Phase 3 prompt config. Deduplicates `what` lists across all nodes.

**Exact file content:**

```json
{
  "model_params": {
    "temperature": 0.2,
    "max_tokens": 3000
  },
  "system_prompt": "You are a curriculum quality reviewer. You will receive all nodes of a learning graph and must identify and remove cross-node duplicate content in 'what' lists.\n\nOverall learning goal: {{learning_goal}}",
  "output_format": {
    "revised_nodes": [
      {
        "node_id": "n1",
        "what": ["Revised subtopic list after removing duplicates"]
      }
    ]
  },
  "rules": [
    "Only output nodes whose 'what' list actually changed. If a node's what list is fine, do NOT include it in revised_nodes.",
    "A duplicate means the SAME concept appears in multiple nodes' what lists. Keep it in the node where it fits best (usually the one conceptually closest to that topic).",
    "Granularity difference is NOT a duplicate: '偏导数的几何意义' in node A and '偏导数的计算方法' in node B are different. Only remove exact or near-identical entries.",
    "Do not reduce any node's what list below 2 items.",
    "Do not add new items. Only remove duplicates.",
    "If no duplicates found, return: {\"revised_nodes\": []}"
  ]
}
```

**Acceptance criteria:**
- File is valid JSON
- `load_ai_config("integration_agent", "all_nodes_json", learning_goal="X")` returns without error

---

### B4 — Add Pydantic models to `models.py`

**File to modify:** `backend/models.py`

**Where to insert:** After the `GenerateGraphAIResult` class (currently line ~377), before `UserBackgroundInput`.

**Exact code to insert:**

```python
# ========== Multi-Agent v2 models ==========


class SkeletonNode(BaseModel):
    """Phase 1 output: single node skeleton"""
    id: str
    name: str
    domain: Optional[str] = None


class SkeletonGraph(BaseModel):
    """Phase 1 output: full graph skeleton"""
    nodes: List[SkeletonNode]
    edges: List[GraphEdge]
    targetNodeId: str


class GeneratedNodeContent(BaseModel):
    """Phase 2 output: content for one node"""
    node_id: str
    why: str
    what: List[str]
    mastery: List[str]
    prompt: str
    resources: List[Resource] = []


class IntegrationRevision(BaseModel):
    """One entry in Phase 3 output"""
    node_id: str
    what: List[str]


class IntegrationResult(BaseModel):
    """Phase 3 output"""
    revised_nodes: List[IntegrationRevision] = []


class GraphNodeV2(BaseModel):
    """Fully assembled node after all 3 phases"""
    id: str
    name: str
    domain: Optional[str] = None
    status: str = "unlearned"
    x: float = 0.0
    y: float = 0.0
    isTarget: bool = False
    why: str = ""
    what: List[str] = []
    mastery: List[str] = []
    prompt: str = ""
    resources: List[Resource] = []


class GenerateGraphV2AIResult(BaseModel):
    """Wrapper returned by ai_service.generate_graph_v2_stream caller"""
    success: bool
    error: Optional[ApiError] = None
```

**Acceptance criteria:**
- `from models import SkeletonNode, SkeletonGraph, GeneratedNodeContent, IntegrationResult, GraphNodeV2, GenerateGraphV2AIResult` succeeds
- All models instantiate without error with minimal required fields

---

### B5 — Add Multi-Agent methods to `AIService`

**File to modify:** `backend/services/ai_service.py`

**Imports to add** at top of file (after existing imports):

```python
import asyncio
from models import (
    # existing imports stay...
    SkeletonGraph, SkeletonNode, GeneratedNodeContent,
    IntegrationResult, GraphNodeV2, GenerateGraphV2AIResult,
)
```

**Methods to add** inside `AIService` class, after `generate_graph()`:

```python
async def _run_phase1(
    self,
    interpretation: str,
    original_input: str,
    user_background: Optional[dict],
    learning_purpose: str,
) -> SkeletonGraph:
    """Phase 1: Curriculum Architect — returns graph skeleton."""
    background_str = (
        json.dumps(user_background, ensure_ascii=False) if user_background else "无"
    )
    params, sys_prompt, usr_prompt = load_ai_config(
        "curriculum_architect",
        interpretation,
        original_input=original_input,
        background=background_str,
        learning_purpose=learning_purpose,
    )
    result = await self.llm_client.chat_json(
        system_prompt=sys_prompt,
        user_prompt=usr_prompt,
        temperature=params.get("temperature", 0.5),
        max_tokens=params.get("max_tokens", 2000),
    )
    return SkeletonGraph(**result)


async def _run_phase2_node(
    self,
    node: SkeletonNode,
    all_nodes: list[SkeletonNode],
    edges: list,
    learning_goal: str,
    learning_purpose: str,
    semaphore: asyncio.Semaphore,
) -> GeneratedNodeContent:
    """Phase 2: Content Generator — generates content for one node."""
    # Compute neighbor names (all other nodes in graph)
    neighbor_names = ", ".join(
        n.name for n in all_nodes if n.id != node.id
    )
    # Compute direct prerequisite names (nodes with edge → this node)
    prerequisite_ids = {e.from_node for e in edges if e.to_node == node.id}
    prerequisite_names = ", ".join(
        n.name for n in all_nodes if n.id in prerequisite_ids
    ) or "无"

    params, sys_prompt, usr_prompt = load_ai_config(
        "content_generator",
        f"{node.id}: {node.name}（领域：{node.domain or '通用'}）",
        learning_goal=learning_goal,
        learning_purpose=learning_purpose,
        neighbor_names=neighbor_names,
        prerequisite_names=prerequisite_names,
    )

    async with semaphore:
        result = await self.llm_client.chat_json(
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            temperature=params.get("temperature", 0.7),
            max_tokens=params.get("max_tokens", 1500),
        )

    # Ensure node_id is always correct regardless of LLM output
    result["node_id"] = node.id
    return GeneratedNodeContent(**result)


async def _run_phase3(
    self,
    contents: list[GeneratedNodeContent],
    learning_goal: str,
) -> IntegrationResult:
    """Phase 3: Integration Agent — deduplicates what lists across nodes."""
    nodes_payload = json.dumps(
        [{"node_id": c.node_id, "name_hint": c.node_id, "what": c.what} for c in contents],
        ensure_ascii=False,
    )
    params, sys_prompt, usr_prompt = load_ai_config(
        "integration_agent",
        nodes_payload,
        learning_goal=learning_goal,
    )
    try:
        result = await self.llm_client.chat_json(
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            temperature=params.get("temperature", 0.2),
            max_tokens=params.get("max_tokens", 3000),
        )
        return IntegrationResult(**result)
    except Exception:
        # Phase 3 failure is non-fatal: return empty revision
        return IntegrationResult(revised_nodes=[])


async def generate_graph_v2_stream(
    self,
    interpretation: str,
    original_input: str,
    user_background: Optional[dict],
    learning_purpose: str,
) -> AsyncGenerator[str, None]:
    """
    Multi-agent graph generation — yields SSE-formatted strings.

    Event sequence:
      {type: "skeleton", data: {nodes, edges, targetNodeId, total_nodes}}
      {type: "node_ready", data: {node_id, why, what, mastery, prompt, resources}}  ×N
      {type: "integration_done", data: {revised_nodes: [{node_id, what}]}}
      {type: "done"}
      {type: "error", data: {code, message}}  — only on fatal failure
    """
    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # ── Phase 1 ──────────────────────────────────────────────
    try:
        skeleton = await self._run_phase1(
            interpretation, original_input, user_background, learning_purpose
        )
    except Exception as e:
        yield _sse({"type": "error", "data": {"code": "PHASE1_FAILED", "message": str(e)}})
        return

    yield _sse({
        "type": "skeleton",
        "data": {
            "nodes": [n.model_dump() for n in skeleton.nodes],
            "edges": [e.model_dump() for e in skeleton.edges],
            "targetNodeId": skeleton.targetNodeId,
            "total_nodes": len(skeleton.nodes),
        },
    })
    await asyncio.sleep(0)

    # ── Phase 2 (concurrent) ──────────────────────────────────
    semaphore = asyncio.Semaphore(8)
    tasks = [
        self._run_phase2_node(
            node=node,
            all_nodes=skeleton.nodes,
            edges=skeleton.edges,
            learning_goal=interpretation,
            learning_purpose=learning_purpose,
            semaphore=semaphore,
        )
        for node in skeleton.nodes
    ]

    # Use asyncio.as_completed to yield node_ready as each finishes
    completed_contents: list[GeneratedNodeContent] = []
    node_futures = [asyncio.ensure_future(t) for t in tasks]

    pending = set(node_futures)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for fut in done:
            try:
                content = fut.result()
                completed_contents.append(content)
                yield _sse({"type": "node_ready", "data": content.model_dump()})
                await asyncio.sleep(0)
            except Exception as e:
                # Non-fatal: yield node_error with the node_id if extractable
                yield _sse({"type": "node_error", "data": {"message": str(e)}})

    # ── Phase 3 ──────────────────────────────────────────────
    integration = await self._run_phase3(completed_contents, interpretation)
    yield _sse({"type": "integration_done", "data": integration.model_dump()})
    await asyncio.sleep(0)

    yield _sse({"type": "done"})
```

**Acceptance criteria:**
- `AIService` has methods: `_run_phase1`, `_run_phase2_node`, `_run_phase3`, `generate_graph_v2_stream`
- `generate_graph_v2_stream` is an `AsyncGenerator[str, None]` (has `yield` statements)
- `_run_phase2_node` uses `async with semaphore:` for rate control
- Phase 3 failure does NOT raise — catches exception and returns empty `IntegrationResult`

---

### B6 — Add SSE endpoint to `routers/ai.py`

**File to modify:** `backend/routers/ai.py`

**Where to insert:** After the existing `generate_graph` endpoint (after line ~140). Do NOT modify the existing `generate_graph` endpoint.

**Exact code to insert:**

```python
@router.post("/generate-graph-v2")
async def generate_graph_v2(
    request: GenerateGraphRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """
    Multi-agent knowledge graph generation — SSE streaming (v2).

    SSE event types:
      skeleton          → {nodes: [{id,name,domain}], edges, targetNodeId, total_nodes}
      node_ready        → {node_id, why, what[], mastery[], prompt, resources[]}
      integration_done  → {revised_nodes: [{node_id, what[]}]}
      done              → {}
      node_error        → {message}   (non-fatal, one node failed)
      error             → {code, message}  (fatal, stream ends)
    """
    ai_service = get_ai_service()
    user_bg = request.userBackground.model_dump() if request.userBackground else None

    return StreamingResponse(
        ai_service.generate_graph_v2_stream(
            interpretation=request.interpretation,
            original_input=request.input,
            user_background=user_bg,
            learning_purpose=request.learning_purpose,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

**Acceptance criteria:**
- `POST /api/ai/generate-graph-v2` is a registered route (visible in `/docs`)
- Route accepts same request body shape as `/api/ai/generate-graph` (`GenerateGraphRequest`)
- Returns `StreamingResponse` with `media_type="text/event-stream"`
- Existing `/api/ai/generate-graph` endpoint is UNCHANGED

---

## FRONTEND TASKS

---

### F1 — Create `src/utils/layoutEngine.js`

**File to create:** `frontend/src/utils/layoutEngine.js`

**Purpose:** Computes `{x, y}` for each node from graph topology. Called once after skeleton event.

**Exact file content:**

```js
/**
 * calculateLayout — BFS topological layout for dependency graphs.
 *
 * Algorithm:
 *   1. Reverse-BFS from targetNodeId to assign topological depth.
 *      depth=0 → target node (y=0)
 *      depth=1 → direct prerequisites of target (y=-250)
 *      depth=N → y = -N * 250
 *   2. Nodes unreachable from target get depth = maxDepth + 1.
 *   3. Within each depth level, group by domain, then space evenly on x-axis.
 *      Groups with same domain are adjacent. Whole level is centered at x=0.
 *
 * @param {Array<{id: string, name: string, domain?: string}>} nodes
 * @param {Array<{from_node: string, to_node: string}>} edges
 * @param {string} targetNodeId
 * @returns {{ [nodeId: string]: { x: number, y: number } }}
 */
export function calculateLayout(nodes, edges, targetNodeId) {
  const Y_STEP = 250;
  const X_STEP = 200;

  // Build reverse adjacency: for each node, who are its prerequisites?
  // edge: from_node → to_node means from_node is prereq of to_node
  // Reverse: to_node → [from_node, ...] means "to_node's parents"
  const parents = {};
  nodes.forEach((n) => { parents[n.id] = []; });
  edges.forEach(({ from_node, to_node }) => {
    if (parents[to_node]) parents[to_node].push(from_node);
  });

  // BFS from target, following parent links to assign depth
  const depth = {};
  const queue = [targetNodeId];
  depth[targetNodeId] = 0;

  while (queue.length > 0) {
    const current = queue.shift();
    const currentDepth = depth[current];
    (parents[current] || []).forEach((parentId) => {
      if (depth[parentId] === undefined) {
        depth[parentId] = currentDepth + 1;
        queue.push(parentId);
      }
    });
  }

  // Nodes not reached by BFS → place below target
  const maxReachedDepth = Math.max(0, ...Object.values(depth));
  nodes.forEach((n) => {
    if (depth[n.id] === undefined) depth[n.id] = maxReachedDepth + 1;
  });

  // Group nodes by depth
  const byDepth = {};
  nodes.forEach((n) => {
    const d = depth[n.id];
    if (!byDepth[d]) byDepth[d] = [];
    byDepth[d].push(n);
  });

  // Assign x within each depth level
  const positions = {};
  Object.entries(byDepth).forEach(([d, levelNodes]) => {
    // Sort by domain so same-domain nodes are adjacent
    const sorted = [...levelNodes].sort((a, b) =>
      (a.domain || "").localeCompare(b.domain || "")
    );

    const count = sorted.length;
    const totalWidth = (count - 1) * X_STEP;
    const startX = -totalWidth / 2;

    sorted.forEach((node, i) => {
      positions[node.id] = {
        x: Math.round(startX + i * X_STEP),
        y: -Number(d) * Y_STEP,
      };
    });
  });

  return positions;
}
```

**Acceptance criteria:**
- `calculateLayout([{id:"n1",name:"A"},{id:"n2",name:"B"}], [{from_node:"n1",to_node:"n2"}], "n2")` returns `{n1: {x:0, y:-250}, n2: {x:0, y:0}}`
- Target node always gets `y=0`
- Nodes with same depth have different `x` values (spread horizontally)
- Function handles empty edges array without error
- Function handles nodes unreachable from target (places them at maxDepth+1)

---

### F2 — Add `generateV2` to `src/services/api.js`

**File to modify:** `frontend/src/services/api.js`

**Where to insert:** In the `aiApi` object, after the existing `generate` method.

**Locate the existing `generate` method** by searching for `buildApiUrl("/ai/generate-graph")`.

**Exact code to insert** (new method in `aiApi` object):

```js
generateV2: async (input, interpretation, learningPurpose, userProfile, { onSkeleton, onNodeReady, onIntegrationDone, onError } = {}) => {
  const body = { input, interpretation, learning_purpose: learningPurpose };
  const userBackground = mapUserProfileToBackground(userProfile);
  if (userBackground) body.userBackground = userBackground;

  const token = tokenManager.get();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(buildApiUrl("/ai/generate-graph-v2"), {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to generate graph (v2)`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop();

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const jsonStr = line.slice(6).trim();
      if (!jsonStr) continue;
      const event = JSON.parse(jsonStr);

      switch (event.type) {
        case "skeleton":
          onSkeleton?.(event.data);
          break;
        case "node_ready":
          onNodeReady?.(event.data);
          break;
        case "integration_done":
          onIntegrationDone?.(event.data);
          break;
        case "node_error":
          // non-fatal: log only
          console.warn("[generateV2] node_error:", event.data);
          break;
        case "error":
          onError?.(event.data);
          throw new Error(event.data?.message || "Graph generation failed");
        case "done":
          return;
        default:
          break;
      }
    }
  }
},
```

**Acceptance criteria:**
- `aiApi.generateV2` is callable
- Calls `POST /ai/generate-graph-v2`
- Invokes `onSkeleton` callback with skeleton data when `type === "skeleton"`
- Invokes `onNodeReady` callback with node content when `type === "node_ready"`
- Invokes `onIntegrationDone` callback when `type === "integration_done"`
- Does NOT break existing `aiApi.generate` function

---

### F3 — Rewrite `GraphGenerationLoader.jsx` for 3-phase UX

**File to modify:** `frontend/src/components/loaders/GraphGenerationLoader.jsx`

**Replace entire file content with:**

```jsx
import { useEffect, useState } from "react";

const PHASE1_LINES = [
  "分析你的学习目标与深度需求...",
  "识别核心知识领域与概念边界...",
  "规划知识依赖链与学习顺序...",
];

export default function GraphGenerationLoader({
  phase = 1,
  skeletonNodeCount = 0,
  readyCount = 0,
  totalCount = 0,
  currentlyProcessing = "",
}) {
  const [visibleLines, setVisibleLines] = useState(0);

  // Phase 1: fade in lines one by one
  useEffect(() => {
    if (phase !== 1) return;
    setVisibleLines(0);
    const timers = PHASE1_LINES.map((_, i) =>
      setTimeout(() => setVisibleLines(i + 1), i * 900)
    );
    return () => timers.forEach(clearTimeout);
  }, [phase]);

  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center overflow-hidden rounded-[28px] bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.12),transparent_36%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,247,250,0.99))] px-8 text-center">

      {/* Decorative graph background dots */}
      <div className="pointer-events-none absolute inset-0 opacity-60">
        {[
          { left: "24%", top: "34%", color: "bg-teal-400", delay: "0ms" },
          { left: "48%", top: "26%", color: "bg-blue-500", delay: "200ms" },
          { right: "28%", top: "38%", color: "bg-cyan-400", delay: "420ms" },
          { left: "34%", bottom: "30%", color: "bg-zinc-400", delay: "130ms" },
          { right: "34%", bottom: "28%", color: "bg-teal-500", delay: "300ms" },
        ].map((dot, i) => (
          <div
            key={i}
            className={`absolute h-3 w-3 animate-pulse rounded-full ${dot.color}`}
            style={{ left: dot.left, top: dot.top, right: dot.right, bottom: dot.bottom, animationDelay: dot.delay }}
          />
        ))}
      </div>

      <span className="mb-4 rounded-full border border-blue-200 bg-white/90 px-4 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-blue-600">
        {phase === 1 ? "Curriculum Design" : phase === 2 ? "Content Generation" : "Integration"}
      </span>

      {/* Phase 1 */}
      {phase === 1 && (
        <>
          <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
            AI 正在规划你的学习路径
          </h3>
          <div className="mb-8 w-full max-w-sm space-y-3 text-left">
            {PHASE1_LINES.map((line, i) => (
              <p
                key={i}
                className="text-sm text-zinc-500 transition-all duration-500"
                style={{ opacity: visibleLines > i ? 1 : 0, transform: visibleLines > i ? "translateY(0)" : "translateY(6px)" }}
              >
                {line}
              </p>
            ))}
          </div>
          <div className="h-2 w-full max-w-md overflow-hidden rounded-full bg-zinc-100">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400" />
          </div>
        </>
      )}

      {/* Phase 2 */}
      {phase === 2 && (
        <>
          <h3 className="mb-2 text-2xl font-semibold tracking-tight text-zinc-900">
            已规划 {skeletonNodeCount} 个知识节点
          </h3>
          <p className="mb-6 text-sm text-zinc-500">AI 正在深度研究每个概念的内容...</p>

          {currentlyProcessing && (
            <div className="mb-6 flex items-center gap-2 rounded-full border border-blue-100 bg-white/90 px-4 py-2 text-sm text-zinc-600 shadow-sm">
              <span className="h-2 w-2 animate-ping rounded-full bg-blue-400" />
              正在研究：{currentlyProcessing}
            </div>
          )}

          <div className="mb-3 flex w-full max-w-md items-center justify-between rounded-3xl border border-zinc-100 bg-white/90 px-5 py-4 shadow-sm">
            <p className="text-sm font-medium text-zinc-700">概念研究进度</p>
            <p className="text-sm font-semibold text-teal-600">
              {readyCount} / {totalCount}
            </p>
          </div>

          <div className="h-2 w-full max-w-md overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-400 via-blue-500 to-cyan-400 transition-all duration-500"
              style={{ width: totalCount > 0 ? `${Math.max(4, (readyCount / totalCount) * 100)}%` : "4%" }}
            />
          </div>
        </>
      )}

      {/* Phase 3 */}
      {phase === 3 && (
        <>
          <h3 className="mb-3 text-2xl font-semibold tracking-tight text-zinc-900">
            正在优化知识关联...
          </h3>
          <p className="text-sm text-zinc-500">整合 {totalCount} 个节点的内容，消除重复</p>
        </>
      )}
    </div>
  );
}
```

**Acceptance criteria:**
- Component accepts props: `phase` (1|2|3), `skeletonNodeCount`, `readyCount`, `totalCount`, `currentlyProcessing`
- Phase 1: shows 3 lines fading in with 900ms stagger
- Phase 2: shows node count, progress bar based on `readyCount/totalCount`, `currentlyProcessing` label
- Phase 3: shows integration message
- No prop type errors when rendered with all-default props

---

### F4 — Add ghost node support to `GraphPage.jsx`

**File to modify:** `frontend/src/pages/GraphPage.jsx`

**This is a surgical change — do NOT rewrite the file. Make only these specific additions.**

#### 4a. Find the node-rendering SVG/div block

Search for the pattern where `data.nodes` (or equivalent state variable holding nodes) are mapped to rendered elements. Look for where individual node cards/circles are rendered with `x` and `y` positioning.

#### 4b. Add ghost node state

In the `GraphPage` component's state declarations, add:

```js
const [ghostNodeIds, setGhostNodeIds] = useState(new Set());
```

`ghostNodeIds` is the set of node IDs that have been received from `skeleton` but not yet from `node_ready`. A node is a ghost until its content arrives.

#### 4c. Add ghost visual style

In the node rendering block, apply these styles conditionally based on whether a node's ID is in `ghostNodeIds`:

```js
// Pseudo-code — adapt to match the actual rendering structure
const isGhost = ghostNodeIds.has(node.id);

// On the node container element:
style={{
  opacity: isGhost ? 0.45 : 1,
  transition: "opacity 0.4s ease, transform 0.4s ease",
  transform: isGhost ? "scale(0.97)" : "scale(1)",
}}

// Inside the node, where content (why/what) would show — conditionally show spinner:
{isGhost ? (
  <div className="flex items-center justify-center py-4">
    <div className="h-5 w-5 animate-spin rounded-full border-2 border-zinc-200 border-t-blue-400" />
  </div>
) : (
  // existing content render
)}
```

#### 4d. Export `setGhostNodeIds` from component scope

Ensure `setGhostNodeIds` is accessible wherever the SSE callback will be called (likely via ref or passed down from `HomePage`). If graph generation lives in `HomePage`, pass `onSkeletonReceived` and `onNodeReady` as props to `GraphPage`, or handle state in `HomePage` before navigating to `GraphPage`.

**Note:** Inspect the actual component structure to determine whether `GraphPage` receives nodes as props or fetches them internally. Adapt accordingly — the key invariant is: when a node is in `ghostNodeIds`, it renders with reduced opacity and a spinner instead of content.

**Acceptance criteria:**
- Nodes in `ghostNodeIds` render at 45% opacity with spinner
- Nodes removed from `ghostNodeIds` animate to full opacity (transition)
- Non-ghost nodes render exactly as before (no regression)

---

### F5 — Wire v2 SSE flow in `HomePage.jsx`

**File to modify:** `frontend/src/pages/HomePage.jsx`

**This is a surgical change. Find the section where `aiApi.generate(...)` is called and add a parallel v2 flow.**

#### 5a. Import new dependencies

At the top of `HomePage.jsx`, ensure these are imported:

```js
import { calculateLayout } from "../utils/layoutEngine";
// aiApi is already imported via: import { aiApi, graphApi, plansApi } from "../services/api";
```

#### 5b. Add v2 loading state

In the component's state declarations, add:

```js
const [generationPhase, setGenerationPhase] = useState(1);   // 1 | 2 | 3
const [skeletonNodeCount, setSkeletonNodeCount] = useState(0);
const [readyNodeCount, setReadyNodeCount] = useState(0);
const [totalNodeCount, setTotalNodeCount] = useState(0);
const [currentlyProcessing, setCurrentlyProcessing] = useState("");
const [pendingNodeIds, setPendingNodeIds] = useState(new Set()); // ghost → ready tracking
```

#### 5c. Replace the `aiApi.generate(...)` call with `aiApi.generateV2(...)`

Find the existing graph generation call. It looks approximately like:

```js
const result = await aiApi.generate(input, interpretation, learningPurpose, userProfile, onProgress);
```

Replace with the v2 call:

```js
// Accumulated state for graph assembly
const skeletonRef = { nodes: [], edges: [], targetNodeId: "" };
const nodeContentsRef = {};

await aiApi.generateV2(
  input,
  interpretation,
  learningPurpose,
  userProfile,
  {
    onSkeleton: (data) => {
      skeletonRef.nodes = data.nodes;
      skeletonRef.edges = data.edges;
      skeletonRef.targetNodeId = data.targetNodeId;

      // Compute layout immediately from topology
      const positions = calculateLayout(data.nodes, data.edges, data.targetNodeId);

      // Build ghost nodes (skeleton + positions, no content yet)
      const ghostNodes = data.nodes.map((n) => ({
        ...n,
        x: positions[n.id]?.x ?? 0,
        y: positions[n.id]?.y ?? 0,
        status: "unlearned",
        isTarget: n.id === data.targetNodeId,
        why: "",
        what: [],
        mastery: [],
        prompt: "",
        resources: [],
      }));

      // Track all nodes as "pending"
      setPendingNodeIds(new Set(data.nodes.map((n) => n.id)));
      setSkeletonNodeCount(data.nodes.length);
      setTotalNodeCount(data.total_nodes);
      setReadyNodeCount(0);
      setGenerationPhase(2);

      // Set ghost nodes into graph state — adapt to however nodes are stored
      // e.g. setNodes(ghostNodes) or dispatch({ type: "SET_GHOST_NODES", nodes: ghostNodes })
      // [ADAPT THIS LINE to match existing state management pattern in HomePage]
    },

    onNodeReady: (content) => {
      nodeContentsRef[content.node_id] = content;

      // Merge content into the ghost node
      // [ADAPT to match existing state management — update the node with matching id]
      // e.g.:
      // setNodes(prev => prev.map(n =>
      //   n.id === content.node_id ? { ...n, ...content, _ghost: false } : n
      // ));

      setPendingNodeIds((prev) => {
        const next = new Set(prev);
        next.delete(content.node_id);
        // Update "currently processing" to next pending node name
        const nextPendingId = [...next][0];
        const nextNode = skeletonRef.nodes.find((n) => n.id === nextPendingId);
        setCurrentlyProcessing(nextNode?.name ?? "");
        return next;
      });

      setReadyNodeCount((prev) => prev + 1);
    },

    onIntegrationDone: (data) => {
      setGenerationPhase(3);
      // Silently update what[] for revised nodes
      if (data.revised_nodes?.length > 0) {
        // [ADAPT to match existing state management]
        // e.g.:
        // setNodes(prev => prev.map(n => {
        //   const revision = data.revised_nodes.find(r => r.node_id === n.id);
        //   return revision ? { ...n, what: revision.what } : n;
        // }));
      }
    },

    onError: (err) => {
      console.error("[generateV2] fatal error:", err);
      // Show error toast / reset loading state
      // [ADAPT to existing error handling pattern]
    },
  }
);

// After generateV2 resolves (type: "done" received):
// Assemble final nodes from skeletonRef + nodeContentsRef
// Proceed to plan creation — same as existing flow after aiApi.generate()
```

#### 5d. Pass phase props to `GraphGenerationLoader`

Find where `<GraphGenerationLoader>` is rendered in `HomePage.jsx` and update its props:

```jsx
<GraphGenerationLoader
  phase={generationPhase}
  skeletonNodeCount={skeletonNodeCount}
  readyCount={readyNodeCount}
  totalCount={totalNodeCount}
  currentlyProcessing={currentlyProcessing}
/>
```

**Acceptance criteria:**
- `onSkeleton` is called before any `onNodeReady`
- `calculateLayout` is called exactly once per generation (in `onSkeleton`)
- Ghost nodes appear immediately after skeleton arrives (before Phase 2 completes)
- `readyNodeCount` increments as each `node_ready` event arrives
- `generationPhase` transitions: `1 → 2` (on skeleton) → `3` (on integration_done)
- After `done`, existing plan-creation flow executes (no regression)
- Existing `aiApi.generate` flow (v1) is not deleted — keep it as fallback or for reference

---

## INVARIANTS (do not violate)

1. **v1 endpoint untouched.** `POST /api/ai/generate-graph` and `ai_service.generate_graph()` must not be modified.
2. **No new npm packages.** `calculateLayout` is pure JS. No dagre, no d3.
3. **Phase 3 is non-fatal.** If `_run_phase3` raises, stream continues and emits `{revised_nodes: []}`.
4. **Semaphore=8.** Phase 2 concurrency cap is `asyncio.Semaphore(8)` — do not remove or raise above 8.
5. **node_id echo.** In `_run_phase2_node`, always overwrite `result["node_id"] = node.id` after LLM response, before constructing `GeneratedNodeContent`.
6. **SSE format.** All events: `f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"` — two newlines, `ensure_ascii=False`.
7. **Positions are integers.** `calculateLayout` returns `{x: Math.round(...), y: ...}` — round x to avoid fractional pixel positions.
8. **Ghost node has all NodeData fields.** Ghost nodes must have all required fields (`what: [], mastery: []`, etc.) so existing node-rendering code doesn't crash on undefined access.
