# ConceptTree Multi-Agent 重构 PRD v2.0

> 日期：2026-05-17  
> 范围：图谱生成系统（generate_graph）重构为 Multi-Agent 三阶段管道

---

## 一、背景与问题

### 当前架构（v1）的核心问题

| 问题 | 根因 |
|------|------|
| 节点数量固定（5-7 / 7-10 / 10-15） | prompt 硬编码数量范围，LLM 按模板输出 |
| 核心内容太浅（what 固定 2-3 个） | output_format 模板固定，LLM 照搬 |
| 节点坐标质量差 | LLM 同时承担内容生成 + 数值布局，注意力被稀释 |
| 生成慢且串行 | parse_goal → generate_graph 两步阻塞，无并发 |
| 内容可能跨节点重复 | 单次大 prompt 同时生成所有节点，无法做跨节点校验 |

### 目标

1. **内容质量**：节点数量和 what 深度由 AI 自主判断，不受硬编码约束
2. **生成速度**：Phase 2 并发生成，总时间接近"最慢单节点时间"而非"所有节点时间之和"
3. **布局稳定**：坐标由前端拓扑算法生成，不依赖 LLM 输出数值
4. **用户信任感**：等待过程可视、有信息密度，用户看得到 AI 在认真工作

---

## 二、整体架构

```
用户输入
   │
   ▼
parse_goal（不变）
   │  interpretation + user_background
   ▼
Phase 1 — Curriculum Architect Agent
   │  输出：图骨架（节点名、domain、edges、targetNodeId）
   │  SSE: {type: "skeleton"}
   ▼
Phase 2 — Content Generator Agent × N（asyncio 并发，Semaphore=8）
   │  每节点独立生成：why / what[] / mastery[] / prompt / resources[]
   │  SSE: {type: "node_ready"}  × N
   ▼
Phase 3 — Integration Agent
   │  跨节点去重，整合 what 列表
   │  SSE: {type: "done"}
   ▼
前端渲染完整图谱
```

---

## 三、后端详细规格

### 3.1 Phase 1 — Curriculum Architect Agent

**职责**：分析学习目标，规划图谱骨架结构。不生成内容，只生成骨架。

**输入**

```
- interpretation: string          # parse_goal 输出的学习目标
- original_input: string          # 用户原始输入
- user_background: dict | null    # 用户背景（strengths / weaknesses）
- learning_purpose: "explore" | "apply" | "master"
```

**输出结构**

```json
{
  "nodes": [
    {
      "id": "n1",
      "name": "链式法则",
      "domain": "数学基础"
    }
  ],
  "edges": [
    {"from_node": "n1", "to_node": "n3"}
  ],
  "targetNodeId": "n5"
}
```

**字段说明**

| 字段 | 说明 | 约束 |
|------|------|------|
| `id` | 节点 ID | `n1`, `n2` ... 格式 |
| `name` | 节点名（中文） | 必填 |
| `domain` | 语义领域标签 | 由 LLM 自由分配，用于前端横轴聚类 |
| `edges` | 有向依赖边（from → to 表示"from 是 to 的前置"） | 无环 |
| `targetNodeId` | 目标节点 | 恰好一个 |

**Prompt 设计要点**

```
节点数量：由你判断，不设上限。简单技能 5 个，深度领域 20+。不要填充，不要截断。
domain：为每个节点分配一个简短的领域标签（中文），相关联的节点应共享同一 domain。
edges：构建合理的前置依赖链，目标节点至少有 2 个入边，不允许循环依赖。
不要输出：x/y 坐标、why/what/mastery/prompt/resources，这些由后续 Agent 处理。
```

**模型参数**：`temperature=0.5`，`max_tokens=2000`（骨架信息量小，不需要 4096）

---

### 3.2 Phase 2 — Content Generator Agent（每节点独立）

**职责**：为单个节点生成完整学习内容。

**输入**（每次调用）

```
- node_id: string
- node_name: string
- domain: string
- learning_goal: string           # 整体学习目标（全局上下文）
- learning_purpose: string
- neighbor_names: list[string]    # 同图内其他节点名称（避免内容重复）
- prerequisite_names: list[string] # 该节点的直接前置节点名（确保内容递进）
```

**输出结构**

```json
{
  "node_id": "n1",
  "why": "为什么要学这个节点（2-3句，联系总学习目标）",
  "what": [
    "具体子主题 1",
    "具体子主题 2"
  ],
  "mastery": [
    "可验证的掌握标准 1",
    "可验证的掌握标准 2"
  ],
  "prompt": "向 AI 导师提问的示例 prompt",
  "resources": [
    {"name": "资源名", "url": "", "reason": "为什么推荐"}
  ]
}
```

**Prompt 设计要点**

```
what 列表：列出该节点下学习者必须掌握的所有子主题。不设固定数量，由内容决定。
  - 基础概念节点：预期 3-5 项
  - 核心算法/理论节点：预期 5-8 项
  - 工具/实践节点：预期 3-6 项
避免重复：已有节点 [neighbor_names] 已覆盖了部分内容，不要重复这些节点的核心主题。
递进感：该节点的前置是 [prerequisite_names]，你的内容应建立在这些基础之上。
mastery：必须是可操作的验证标准（能做什么 / 能解释什么），不要写抽象描述。
```

**并发控制**

```python
semaphore = asyncio.Semaphore(8)

async def generate_node(node_skeleton):
    async with semaphore:
        return await _run_phase2_node(node_skeleton, ...)

results = await asyncio.gather(*[generate_node(n) for n in nodes])
```

**模型参数**：`temperature=0.7`，`max_tokens=1500`（单节点内容，无需 4096）

---

### 3.3 Phase 3 — Integration Agent

**职责**：检查所有节点的 what 列表，消除跨节点重复，确保整体图谱内容不冗余。

**输入**

```
- all_nodes: list[{node_id, name, what[]}]  # Phase 2 全部输出
- learning_goal: string
```

**输出结构**

```json
{
  "revised_nodes": [
    {
      "node_id": "n1",
      "what": ["修订后的子主题 1", "子主题 2"]
    }
  ]
}
```

**Prompt 设计要点**

```
任务：检查以下节点的 what 列表，找出跨节点重复或高度重叠的条目。
处理规则：
  - 若某个子主题在多个节点出现，保留在最合适的节点，其余节点删除。
  - 若是同一概念的不同粒度，保留，不是重复。
  - 不要无故删减内容，只处理真实重复。
只输出需要修改的节点，未修改的节点不输出。
```

**模型参数**：`temperature=0.2`，`max_tokens=3000`

---

### 3.4 SSE Streaming Endpoint

**端点**：替换现有 `POST /api/generate-graph`（或新增版本路由）

**事件协议**

```
# Phase 1 完成后发送
data: {"type": "skeleton", "data": {
  "nodes": [{"id": "n1", "name": "链式法则", "domain": "数学基础"}],
  "edges": [{"from_node": "n1", "to_node": "n3"}],
  "targetNodeId": "n5",
  "total_nodes": 12
}}

# Phase 2 每完成一个节点发送
data: {"type": "node_ready", "data": {
  "node_id": "n1",
  "why": "...",
  "what": ["...", "..."],
  "mastery": ["...", "..."],
  "prompt": "...",
  "resources": []
}}

# Phase 3 完成后发送（仅包含有修改的节点）
data: {"type": "integration_done", "data": {
  "revised_nodes": [{"node_id": "n2", "what": ["...修订后..."]}]
}}

# 全部完成
data: {"type": "done"}

# 错误
data: {"type": "error", "data": {"code": "PHASE1_FAILED", "message": "..."}}
```

**错误处理**

| 场景 | 处理方式 |
|------|---------|
| Phase 1 失败 | 发 `error` 事件，终止整个流程 |
| Phase 2 某节点失败 | 发 `node_error` 事件（含 node_id），该节点显示占位内容，其余继续 |
| Phase 3 失败 | 忽略，直接发 `done`，使用 Phase 2 原始输出 |

---

## 四、前端详细规格

### 4.1 布局算法 `calculateLayout(nodes, edges, targetNodeId)`

**算法：BFS 拓扑分层 + domain 横向聚类**

```
输入：
  nodes: [{id, name, domain}]
  edges: [{from_node, to_node}]
  targetNodeId: string

输出：
  positions: {[nodeId]: {x: number, y: number}}
```

**步骤**

```
Step 1 — 计算每个节点的拓扑深度（depth）
  从 targetNodeId 出发，沿边反向 BFS
  target → depth 0
  target 的直接前置节点 → depth 1
  前置的前置 → depth 2
  以此类推

Step 2 — 计算 y 坐标
  y = -depth × 250
  target node: y = 0

Step 3 — 计算 x 坐标
  按 depth 分组，每组内：
    - 按 domain 排序（相同 domain 的节点相邻）
    - 均匀分布在 x 轴，间距 200
    - 整组水平居中（中心对齐 x=0）

Step 4 — 孤立节点处理（无入边无出边，BFS 未覆盖）
  放置在图谱最底部（y = maxDepth × 250 + 250），x 均匀分布
```

**示例输出**

```
depth=2    [导数基础 x=-200]  [矩阵运算 x=0]  [概率论 x=200]
depth=1    [链式法则 x=-100]  [梯度下降 x=100]
depth=0                [反向传播(target) x=0]
```

---

### 4.2 三阶段 Loading 体验

#### 阶段一：Phase 1 运行中

```
UI 元素：
  - 标题："AI 正在规划你的学习路径"
  - 三行 fade-in 文案（依次出现）：
      "分析你的学习目标与深度需求..."
      "识别核心知识领域与概念边界..."
      "规划知识依赖链与学习顺序..."
  - 模糊进度条（无真实进度，仅动画）
```

#### 阶段二：Phase 1 完成，骨架渲染

```
UI 元素：
  - 图谱骨架出现（ghost 节点 + edges）
    - ghost 节点：灰色边框、名称可见、内容区显示 spinner
  - 提示文案："已规划 {N} 个知识节点，正在深度研究每个概念..."
  - 底部进度："{received} / {total} 个概念已完成"
  - 右上角轮播："正在研究：{当前处理中的节点名}"
```

#### 阶段三：Phase 2 节点逐个点亮

```
每收到一个 node_ready 事件：
  - 对应 ghost 节点执行 reveal 动画（淡入 + 轻微缩放）
  - 节点显示完整内容（why preview + what count）
  - 计数器更新
  - "正在研究" 标签切换到下一个仍在处理中的节点名
```

#### 阶段四：Phase 3 完成

```
若有 revised_nodes：静默更新对应节点的 what 列表（无需动画）
发 done 事件后：移除 loading overlay，图谱进入可交互状态
```

---

### 4.3 节点状态机

```
skeleton_received → ghost
node_ready        → ghost → loaded（reveal 动画）
node_error        → ghost → error_fallback（显示占位内容）
integration_done  → loaded → updated（静默更新 what）
done              → 全部进入 interactive 状态
```

---

### 4.4 布局保存与重置

**方案 A（当前实现）**：用户拖拽覆盖算法初始坐标，保存到后端（逻辑不变）

**方案 B（后续迭代）**：图谱工具栏新增"重置布局"按钮
```
点击 → 重新调用 calculateLayout() → 更新所有节点坐标 → 批量保存到后端
```

---

## 五、数据结构变更

### Phase 1 输出（新）vs 当前 generate_graph 输出（旧）

| 字段 | 旧（单次生成） | 新 Phase 1 骨架 | 新 Phase 2 内容 |
|------|--------------|----------------|----------------|
| id | ✓ | ✓ | - |
| name | ✓ | ✓ | - |
| domain | - | ✓（新增） | - |
| x / y | ✓（LLM 生成） | ✗（前端算法） | - |
| why | ✓ | ✗ | ✓ |
| what[] | ✓（固定2-3个） | ✗ | ✓（自由数量） |
| mastery[] | ✓（固定2个） | ✗ | ✓（自由数量） |
| prompt | ✓ | ✗ | ✓ |
| resources[] | ✓ | ✗ | ✓ |
| phase / phase_order | ✓ | ✗（废弃） | - |
| depth_level | ✓ | ✗（废弃） | - |
| isTarget | ✓ | ✓（通过 targetNodeId 推算） | - |
| status | ✓ | ✓（默认 unlearned） | - |

> `phase` / `phase_order` / `depth_level` 字段从 LLM 职责中完全移除，前端布局改为拓扑算法驱动。

---

## 六、非功能需求

| 指标 | 目标 |
|------|------|
| Phase 1 完成时间 | ≤ 5 秒（骨架信息量小，max_tokens=2000） |
| Phase 2 总完成时间 | ≤ 15 秒（8 并发，单节点 ≤ 8 秒） |
| Phase 3 完成时间 | ≤ 5 秒 |
| 端到端总时间 | ≤ 25 秒（含网络） |
| Phase 2 最大并发 | Semaphore(8)，避免 API 限流 |
| Phase 2 单节点失败 | 不影响其他节点，显示占位内容 |

---

## 七、实现顺序

```
Sprint 1 — 后端核心（不上线，本地验证）
  1. 新建 configs/curriculum_architect.json（Phase 1 prompt）
  2. 新建 configs/content_generator.json（Phase 2 prompt）
  3. 新建 configs/integration_agent.json（Phase 3 prompt）
  4. ai_service.py 新增 generate_graph_v2()：
       _run_phase1() → asyncio.gather(_run_phase2_node × N) → _run_phase3()
  5. 新增 SSE endpoint /api/generate-graph-v2

Sprint 2 — 前端骨架渲染
  6. 实现 calculateLayout() 拓扑算法
  7. 更新 SSE event handler（接收 skeleton / node_ready / done）
  8. 新增 ghost 节点渲染逻辑
  9. 改造 GraphGenerationLoader（三阶段 UI）

Sprint 3 — 节点点亮动画 + 收尾
  10. ghost → loaded reveal 动画
  11. integration_done 静默更新 what 列表
  12. 错误状态处理（node_error 占位）

Sprint 4 — 方案 B（后续）
  13. 工具栏"重置布局"按钮
```

---

## 八、范围外（本版本不做）

- Prompt 自动迭代 Agent（另立 PRD）
- parse_goal 换快模型（用户决定不降质量，暂不做）
- 节点数量硬性上限（由 Phase 1 prompt 的 rules 软性约束）
- 用户对 Phase 1 骨架的人工干预（先自动完成，后续可迭代）
