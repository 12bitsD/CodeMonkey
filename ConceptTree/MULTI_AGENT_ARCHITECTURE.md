# ConceptTree Multi-Agent 架构分析

## 总览

当前项目里的 multi-agent 不是 LangChain、CrewAI、AutoGen 这类外部 Agent 框架，而是一个自研的轻量多 Agent 编排流程。

它用 FastAPI、asyncio、SSE 和 JSON Prompt Config 手写了一个三阶段流水线：

```text
Curriculum Architect -> Content Generator x N -> Integration Agent
```

本质上是一个 Planner / Map / Reducer 架构：

- Planner：先规划知识图谱骨架
- Map：对每个节点并行生成学习内容
- Reducer：最后做全局整合与去重

## 技术栈

### 后端

- Python
- FastAPI
- StreamingResponse
- Server-Sent Events
- asyncio
- Pydantic
- JSON prompt config
- OpenAI-compatible LLM client

关键文件：

- `backend/services/ai_service.py`
- `backend/routers/ai.py`
- `backend/models.py`
- `backend/services/llm/configs/curriculum_architect.json`
- `backend/services/llm/configs/content_generator.json`
- `backend/services/llm/configs/integration_agent.json`

### 前端

- React
- Vite
- fetch + ReadableStream
- TextDecoder
- React state
- 自定义图谱布局算法

关键文件：

- `frontend/src/services/api.js`
- `frontend/src/pages/HomePage.jsx`
- `frontend/src/components/loaders/GraphGenerationLoader.jsx`
- `frontend/src/utils/layoutEngine.js`
- `frontend/src/pages/GraphPage.jsx`

## 三个 Agent

### 1. Curriculum Architect

配置文件：

```text
backend/services/llm/configs/curriculum_architect.json
```

职责：

- 生成知识图谱骨架
- 决定节点数量
- 决定节点名称
- 决定节点领域标签
- 决定依赖边
- 决定目标节点

它不生成节点内容，不负责：

- why
- what
- mastery
- prompt
- resources
- 坐标

这样做的好处是把“结构设计”和“内容生成”拆开，避免一个大 prompt 同时处理太多任务。

### 2. Content Generator

配置文件：

```text
backend/services/llm/configs/content_generator.json
```

职责：

- 对单个节点生成学习内容
- 生成 why
- 生成 what
- 生成 mastery
- 生成 prompt
- 生成 resources

每个节点会触发一次独立 LLM 调用。

输入上下文包括：

- 当前节点 id
- 当前节点名称
- 当前节点 domain
- 整体学习目标
- 学习目的
- 邻居节点名称
- 直接前置节点名称

这里采用并发执行，但通过 `asyncio.Semaphore(8)` 把最大并发限制为 8，避免请求过载。

### 3. Integration Agent

配置文件：

```text
backend/services/llm/configs/integration_agent.json
```

职责：

- 接收所有节点的内容
- 检查跨节点重复的 `what` 条目
- 返回需要修改的节点
- 只修改 `what` 列表

它是非致命阶段。

如果 Integration Agent 失败，后端不会让整次生成失败，而是返回：

```json
{
  "revised_nodes": []
}
```

## 后端运行链路

入口是：

```text
POST /api/ai/generate-graph-v2
```

对应文件：

```text
backend/routers/ai.py
```

路由会调用：

```python
ai_service.generate_graph_v2_stream(...)
```

这个方法是一个异步生成器，持续 yield SSE 字符串。

SSE 格式统一为：

```python
f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

事件顺序：

```text
skeleton
node_ready x N
node_error 可选
integration_done
done
error 可选
```

### Phase 1

调用 `_run_phase1`。

流程：

1. 加载 `curriculum_architect.json`
2. 调用 `llm_client.chat_json(...)`
3. 用 `SkeletonGraph(**result)` 校验结构
4. 过滤非法 edge
5. 如果 `targetNodeId` 不存在，则 fallback 到最后一个节点
6. 通过 SSE 发出 `skeleton`

### Phase 2

调用 `_run_phase2_node`。

流程：

1. 为每个 skeleton node 创建一个异步任务
2. 用 `asyncio.Semaphore(8)` 控制并发
3. 每个节点单独调用 `content_generator`
4. 使用 `asyncio.wait(... FIRST_COMPLETED)` 监听谁先完成
5. 每完成一个节点，就通过 SSE 发出 `node_ready`
6. 如果单个节点失败，发出 `node_error`，不中断其他节点

### Phase 3

调用 `_run_phase3`。

流程：

1. 收集所有 `GeneratedNodeContent`
2. 提取每个节点的 `what`
3. 调用 `integration_agent`
4. 返回 `IntegrationResult`
5. 通过 SSE 发出 `integration_done`
6. 最后发出 `done`

## 前端运行链路

前端入口在：

```text
frontend/src/services/api.js
```

方法：

```js
aiApi.generateV2(...)
```

它使用：

```js
fetch(...)
res.body.getReader()
TextDecoder()
```

逐行读取 SSE：

```js
if (!line.startsWith("data: ")) continue;
const event = JSON.parse(line.slice(6).trim());
```

然后按事件类型调用回调：

- `onSkeleton`
- `onNodeReady`
- `onIntegrationDone`
- `onError`

## HomePage 中的组装逻辑

文件：

```text
frontend/src/pages/HomePage.jsx
```

生成过程中维护三个临时对象：

```js
const skeletonRef = { nodes: [], edges: [], targetNodeId: "", positions: {} };
const nodeContentsRef = {};
let integrationRevisions = [];
```

### 收到 skeleton

前端会：

1. 保存 skeleton nodes
2. 保存 edges
3. 保存 targetNodeId
4. 调用 `calculateLayout(...)` 计算坐标
5. 切换 loader 到 Phase 2
6. 初始化节点总数和进度

### 收到 node_ready

前端会：

1. 把节点内容写入 `nodeContentsRef`
2. 从 pending 节点集合中移除该节点
3. 更新 ready count
4. 更新当前正在处理的节点名

### 收到 integration_done

前端会：

1. 切换 loader 到 Phase 3
2. 保存 revised nodes

### 收到 done

`generateV2` 返回后，HomePage 会把所有中间结果合并成最终图谱：

```text
skeleton node + layout position + generated content + integration revision
```

然后调用：

```js
actions.createPlan(...)
```

创建学习计划并跳转到正式图谱页。

## 布局算法

文件：

```text
frontend/src/utils/layoutEngine.js
```

当前布局基于依赖边的拓扑关系。

边的含义是：

```text
from_node 是前置知识
to_node 依赖 from_node
```

因此布局方向是：

```text
前置基础
  ↓
核心目标
  ↓
应用/后续节点
```

实现上会：

1. 规范化 edge 字段
2. 建立 parents / children / indegree
3. 用拓扑排序计算每个节点深度
4. 对每层节点按 domain/name/id 排序
5. 做轻量 barycentric pass，让依赖边更接近垂直路径
6. 输出 `{ nodeId: { x, y } }`

## 加载体验

文件：

```text
frontend/src/components/loaders/GraphGenerationLoader.jsx
```

加载态分为三阶段：

1. Curriculum Design
   - 分析目标
   - 识别知识领域
   - 规划依赖链

2. Content Generation
   - 展示 skeleton 节点数量
   - 展示 `readyCount / totalCount`
   - 展示当前处理节点

3. Integration
   - 展示整合与去重状态

## 架构优点

- 比单次大 prompt 更稳定
- 结构生成和内容生成职责清晰
- Phase 2 可以并发，速度更好
- SSE 可以把生成进度实时反馈给前端
- Pydantic 能尽早发现 LLM 输出结构错误
- Prompt 配置文件独立，便于迭代 Agent 行为
- Integration Agent 失败不会导致整次生成失败

## 架构限制

- 这是角色化多次 LLM 调用，不是完整自主 Agent 框架
- 没有工具调用规划
- 没有 Agent 长期记忆
- 没有复杂 retry / backoff / cost control
- Phase 2 单节点失败后，目前只是发 `node_error`
- Phase 3 只做 `what` 去重，不做结构级修复
- 当前前端不是生成中实时进入 GraphPage，而是生成完成后创建 plan 再跳转

## 一句话总结

ConceptTree 当前的 multi-agent 是一个基于 FastAPI SSE、asyncio 并发、Pydantic 校验和 JSON Prompt Config 的轻量多 Agent 图谱生成流水线。

它的核心思想是：

```text
先规划结构，再并行填充节点内容，最后全局整合。
```
