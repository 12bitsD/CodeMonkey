# ConceptTree - Harness Engineering AI 稳定性与提醒优化计划

## 背景

本次排查覆盖 5 个症状：

1. 打开节点时卡顿，偶尔节点详情加载不出来。
2. AI 解释 / 聊天在刷新、切换节点、重复点击后可能产生并发请求，前端状态被旧请求覆盖，后端连接与 LLM 请求被放大。
3. AI 功能不可用。
4. 首页“正在生成今日推荐节点...”有时长期停留。
5. 首页“未设置截止日期”没有可操作入口，节点级截止日期尚未建模。

## 已确认问题

### P0 - AI 请求失败的直接原因

后端日志显示主 LLM 请求返回 `401 Invalid API Key`，说明当前 `LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1` 已打到 MiMo Token Plan China 入口，但 `LLM_API_KEY` 不是有效的 Token Plan China key。

同时 `.env` 中 `LLM_FALLBACK_ENABLED=true`，但 fallback key 是占位值，导致一次 AI 失败会继续请求 fallback，再失败一次，放大等待时间和错误噪声。

### P0 - SSE 请求缺少前端取消与去重

`aiApi.explainTopic` 和 `aiApi.chatStream` 原先没有 `AbortController`。

影响：

- 切换节点后，旧请求仍可能继续写入当前状态。
- 重复点击 AI 解释时，可能同一个 topic 同时跑多个请求。
- 页面刷新 / 返回 / 关闭节点时，浏览器和后端之间容易留下半开流。

### P1 - 数据库连接池可能复用断开的 Supabase 连接

日志出现 `psycopg2.OperationalError: SSL SYSCALL error: EOF detected`。

这通常是池中连接被 Supabase / 网络层关闭后继续复用导致。节点打开、今日推荐、计划列表都依赖 DB，都会受到影响。

### P1 - 今日推荐过度依赖 AI 同步返回

首页今日提醒会立即请求 `/api/ai/recommend-next`。当 LLM key 无效或 fallback 重试时，UI 会长时间显示“正在生成今日推荐节点...”。这个推荐应该具备短超时、可取消、可降级。

### P2 - 截止日期只有计划级字段，没有节点级字段

当前后端已有 `plans.target_end_date` 和 `PUT /api/plans/{id}`，适合做计划级截止日期。

但节点级截止日期没有：

- `nodes.target_end_date` 字段
- 节点更新接口
- 节点提醒算法
- 前端节点详情设置入口

## 本轮已落地修复

### 1. 前端 SSE 取消与防重复

文件：

- `frontend/src/services/api.js`
- `frontend/src/pages/GraphPage.jsx`

改动：

- `aiApi.explainTopic` 支持 `signal`。
- `aiApi.chatStream` 支持 `signal`。
- 切换节点 / 组件卸载时 abort 解释与聊天请求。
- 同一个 topic 正在 loading 时重复点击直接忽略。
- abort 后清理空 loading 状态，避免再次打开节点时卡在 loading。

### 2. 节点打开性能优化

文件：

- `frontend/src/hooks/useGraphInteraction.js`

改动：

- `selectedNode` 从 `nodes.find` 改为基于 `nodeMap` O(1) 查找。
- 推荐节点的前置依赖判断从嵌套 `filter/find` 改为 `prerequisiteMap + nodeMap`。

### 3. 今日推荐防悬挂

文件：

- `frontend/src/pages/HomePage.jsx`

改动：

- 首页 `recommendNext` 请求增加 `AbortController`。
- 增加 15 秒超时，避免“正在生成今日推荐节点...”无限挂起。
- 组件卸载或 plan 切换时取消旧请求。

### 4. 截止日期入口

文件：

- `frontend/src/pages/HomePage.jsx`

改动：

- 今日提醒中无截止日期时展示“设置截止日期”按钮。
- 计划卡片无截止日期时展示“设置截止日期”按钮。
- 新增截止日期 Modal，通过既有 `actions.updatePlan -> PUT /api/plans/{id}` 保存。

### 5. 后端 DB 池断线恢复

文件：

- `backend/database.py`

改动：

- 从连接池取连接时，如果连接已关闭或配置连接时报 `InterfaceError / OperationalError`，丢弃该连接并重试一次。

### 6. 禁用无效 fallback

文件：

- `backend/.env`
- `backend/config.py`

改动：

- 默认 `LLM_FALLBACK_ENABLED=false`。
- 本地 `.env` 关闭 fallback，并清空占位 fallback key。

## 仍需用户确认 / 配置

### MiMo Token Plan China Key

当前 AI 失败的根因是 MiMo 返回 401。请在 `backend/.env` 中把 `LLM_API_KEY` 换成 MiMo Token Plan China 控制台生成的有效 key。

目标配置：

```env
LLM_PROVIDER=mimo_token_plan_cn
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
LLM_MODEL=mimo-v2.5-pro
LLM_FALLBACK_ENABLED=false
```

注意：这里必须是 Token Plan China 专用 key，不是普通 MiMo API key，也不是 Moonshot/Kimi key。

## 下一阶段优化计划

### Sprint A - AI 请求 Harness

目标：所有 AI 流式调用都有可取消、可去重、可观测状态。

任务：

1. 增加 `frontend/src/utils/aiRequestRegistry.js`，统一管理 `AbortController`、requestId、dedupe key。
2. `explainTopic` 使用 key：`explain:${planId}:${nodeId}:${topicIndex}`。
3. `chatStream` 使用 key：`chat:${planId}:${nodeId}`。
4. 后端 SSE 捕获客户端断连，停止继续请求 LLM 或写缓存。
5. 增加测试：切节点后旧请求不能写入新节点状态。

验收：

- 快速重复点击 AI 解释只产生 1 个有效请求。
- 切换节点后旧请求返回不会污染当前节点。
- abort 不显示“回复失败 / 解释失败”。

### Sprint B - 今日推荐降级

目标：推荐节点不能被 LLM 可用性拖垮。

任务：

1. 后端 `/api/ai/recommend-next` 先计算 deterministic recommendation。
2. LLM 成功时只补充更自然的 reason。
3. LLM 失败或超时时返回 deterministic 结果。
4. 首页展示“推荐暂用本地规则生成”而不是无限 loading。

验收：

- LLM key 无效时接口仍 200。
- 首页不超过 3 秒显示推荐或空态。

### Sprint C - 节点详情性能

目标：打开节点稳定在轻量渲染路径内。

任务：

1. 将 Node Detail Drawer 拆出 `NodeDetailDrawer.jsx` 并 `React.memo`。
2. 预计算 `outgoingEdgesByNodeId`、`resourcesByNodeId`。
3. MarkdownContent 对 AI 解释内容懒渲染，只在 expanded 时渲染。
4. 资源搜索与 AI 解释状态按 nodeId 分桶，减少全局对象更新。

验收：

- 100 节点 / 200 边图谱下，点击节点无明显卡顿。
- 拖动画布时 drawer 不做无关重渲染。

### Sprint D - 节点级截止日期

目标：计划和节点都能设置截止日期。

后端：

1. `nodes` 增加 `target_end_date TIMESTAMPTZ`。
2. `GraphNode` / 序列化增加 `targetEndDate`。
3. 新增或复用节点更新接口：`PUT /api/plans/{plan_id}/nodes/{node_id}`。
4. 节点 owner 校验沿用 plan ownership。

前端：

1. 节点详情 drawer 增加“节点截止日期”设置。
2. 图谱节点卡片显示临近截止状态。
3. 今日提醒优先级纳入节点截止日期。

验收：

- 节点截止日期刷新后保留。
- 今日提醒可优先提示临近截止节点。

## Harness 守门建议

### PostToolUse: AI 相关文件变更

触发路径：

- `frontend/src/services/api.js`
- `frontend/src/pages/GraphPage.jsx`
- `backend/routers/ai.py`
- `backend/services/llm/**`

自动运行：

```powershell
cd frontend
npm run test:unit -- api.sprint3.test.js

cd ../backend
python -m pytest tests/test_chat_stream_fallback.py tests/test_recommend_next_api.py -q
```

### PostToolUse: 计划提醒相关文件变更

触发路径：

- `frontend/src/pages/HomePage.jsx`
- `frontend/src/utils/planReminders.js`
- `backend/routers/plans.py`
- `backend/models.py`

自动运行：

```powershell
cd frontend
npm run test:unit -- HomePage.recommendation.test.jsx planReminders.test.js

cd ../backend
python -m pytest tests/test_plan_management_api.py tests/test_recommend_next_api.py -q
```

### Stop: 回归套件

```powershell
cd frontend
npm run build
npm run test:unit -- HomePage.loading.test.jsx HomePage.recommendation.test.jsx api.sprint3.test.js

cd ../backend
python -m py_compile database.py services/llm/client.py services/llm/providers/openai_compatible.py
python -m pytest tests/test_chat_stream_fallback.py tests/test_recommend_next_api.py tests/test_plan_management_api.py -q
```

## 风险与回滚

| 风险 | 影响 | 回滚方式 |
| --- | --- | --- |
| AbortController 误杀正在显示的流 | AI 内容提前停止 | 回滚 `GraphPage.jsx` 的 abort refs 与 `api.js` signal 参数 |
| DB 连接重试隐藏真实网络问题 | 日志更少但问题仍在 | 增加 acquire 失败日志与连接池重建 |
| 首页推荐 15 秒超时过短 | 慢模型下不显示 AI 推荐 | 改为 30 秒或后端 deterministic fallback |
| 节点级截止日期扩 schema | 迁移风险 | 先做 plan 级入口，节点级单独 Sprint |

## 当前结论

本轮已经处理“请求不取消 / 重复请求 / 今日推荐无限 loading / 计划截止日期无入口 / DB 池复用断线连接”的直接问题。

AI 仍需替换为有效 MiMo Token Plan China key 后才能恢复真实回答。

## 2026-05-15 维护开发更新

### 已继续落地

1. Sprint A - AI 请求 Harness
   - 新增 `frontend/src/utils/aiRequestRegistry.js`，统一管理 `AbortController`、`requestId`、dedupe key。
   - `GraphPage.jsx` 的 AI 解释使用 `explain:${planId}:${nodeId}:${topicIndex}` 去重。
   - `GraphPage.jsx` 的聊天使用 `chat:${planId}:${nodeId}`，新请求会取消同 key 旧请求。
   - 节点切换和组件卸载时统一 abort 活跃 AI 请求，旧流 chunk 不再写入新节点状态。
   - 后端 `explain-topic` / `chat` SSE 发现客户端断开时停止继续输出。

2. Sprint B - 今日推荐降级
   - `/api/ai/recommend-next` 先计算 deterministic recommendation。
   - LLM 成功时返回 AI reason，并标记 `recommendation_source=ai`。
   - LLM 失败、超时或 key 无效时仍返回 200 和本地推荐，并标记 `recommendation_source=local`。
   - 本地推荐优先选择前置依赖已满足的未学习节点；有节点截止日期时优先更临近的节点。

3. Sprint D - 节点级截止日期
   - `nodes` 增加 `target_end_date TIMESTAMPTZ`。
   - `NodeData` / `NodeBase` / `NodeUpdate` 增加 `targetEndDate`。
   - 新增 `PUT /api/plans/{plan_id}/nodes/{node_id}`，支持更新节点截止日期。
   - `GET /api/plans/{plan_id}/graph` 返回节点 `targetEndDate`。
   - 图谱节点详情抽屉新增“节点截止日期”设置与清除入口，刷新后保留。

### 本轮验证

```powershell
cd frontend
npm run test:unit -- aiRequestRegistry.test.js api.sprint3.test.js HomePage.recommendation.test.jsx
npm run build

cd ../backend
python -m py_compile routers\ai.py routers\graph.py routers\plans.py models.py
```

后端 pytest 集成测试在连接 Supabase 测试库阶段失败，报错为 `server closed the connection unexpectedly`，用例未实际执行；需要数据库连接恢复后再跑：

```powershell
python -m pytest tests/test_recommend_next_api.py tests/test_graph.py tests/test_plan_management_api.py -q
```

## 2026-05-16 AI 生成慢与自动化验收更新

### 新发现

1. AI 解释失败截图中的“解释生成失败”仍可能由 LLM 真实失败触发；当前前端 abort/去重已经接上，但无法把无效 key 或上游错误变成成功回答。
2. 后端日志出现 Supabase pooler `EAUTHTIMEOUT timeout while waiting for message`，这会拖慢所有需要 DB ownership/cache 读取的 AI 入口。
3. 非流式 LLM 调用原先默认最多重试 3 次；当 key 无效、模型名错误、权限不足这类不可恢复错误出现时，重试只会放大等待时间。

### 已追加修复

- `backend/database.py`：连接池创建增加 `connect_timeout`，默认 5 秒，避免 DB 连接挂很久。
- `backend/config.py`：新增 `DB_CONNECT_TIMEOUT`，并将默认 `LLM_MAX_RETRIES` 从 3 降为 2。
- `backend/services/llm/client.py`：对 `400/401/403/404` 这类不可恢复 LLM Provider 错误快速失败，不再 backoff 重试。
- `frontend/src/services/api.sprint3.test.js`：补充 `AbortController.signal` 传递测试。
- `backend/tests/unit/test_llm_fast_fail.py`：补充 LLM 认证失败不重试、可恢复错误仍重试的单元测试。
- `backend/tests/conftest.py`：`no_db` 单元测试真正跳过 Supabase fixture，避免自动化测试被 DB 连接拖慢。
- 新增 `scripts/test_ai_stability.ps1`，用于一键检查 AI 稳定性优化成果。

### 自动化检查脚本

默认不依赖 Supabase 集成库：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_ai_stability.ps1
```

需要同时验证 DB 集成接口时：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_ai_stability.ps1 -IncludeDbIntegration
```

脚本覆盖：

- 前端 AI 请求 registry 去重/abort。
- `explainTopic` / `chatStream` SSE signal 透传。
- 首页推荐的本地降级。
- 后端 LLM 401 快速失败。
- 后端 stream fallback 行为。
- 静态守门：关键优化代码仍存在。

### 本次验证结果

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_ai_stability.ps1 -SkipBuild
npm run build
python -m py_compile config.py database.py services\llm\client.py services\llm\providers\openai_compatible.py
```

结果：全部通过。默认脚本耗时约 4-5 秒；需要 DB 的集成测试仍建议在 Supabase pooler 稳定时单独运行。
