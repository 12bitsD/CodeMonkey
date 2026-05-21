# ConceptTree - Harness Engineering Supabase 稳定性优化 AI Coding Plan

## 背景

ConceptTree 当前大量核心功能依赖 Supabase/Postgres：

- 首页计划列表、今日提醒、今日推荐节点。
- 图谱加载、节点状态、节点位置、节点截止日期。
- 笔记列表、AI 解释保存为笔记、聊天总结保存为笔记。
- 学习记录、用户画像、统计页。

上一次节点截止日期错误暴露出一个产品级风险：**一个局部数据库错误可能扩散为整页失败、全局状态异常，甚至让用户感觉“全盘崩溃”**。

本计划目标是把 Supabase 交互从“接口成功才正常”升级为“接口失败也可控、可恢复、可观测、可回归测试”。

## Harness Engineering 原则

### 1. Blast Radius Control

任何 Supabase 单点失败都不能造成整页白屏、全局状态清空、用户输入丢失或进程崩溃。

### 2. Explicit Failure Contract

数据库错误必须被映射成稳定的 API 错误码，而不是裸露 `psycopg2` 异常、随机 500 或无结构响应。

### 3. Bounded Work

所有数据库交互必须有明确边界：连接超时、查询超时、锁等待超时、事务边界、重试次数上限。

### 4. Idempotent User Actions

用户连续点击、刷新后重试、请求中断后再次提交，不应该造成重复写入、状态错乱或部分提交。

### 5. Release Gates

每一类数据库风险都必须有自动化测试覆盖，并纳入上线前稳定性脚本。

## 当前已落地的基础防护

### 数据库连接超时

文件：

- `backend/config.py`
- `backend/database.py`

已增加：

- `DB_CONNECT_TIMEOUT`
- `DB_STATEMENT_TIMEOUT_MS`
- `DB_LOCK_TIMEOUT_MS`
- `DB_IDLE_IN_TX_TIMEOUT_MS`

目标：

- Supabase 连接慢时快速失败。
- 查询卡住时快速释放请求。
- DDL/更新锁等待时不要拖死接口。
- 事务悬挂时由数据库主动回收。

### 数据库异常统一响应

文件：

- `backend/main.py`

已增加：

- `PoolError -> 503 DATABASE_UNAVAILABLE`
- `OperationalError -> 503 DATABASE_UNAVAILABLE`
- `InterfaceError -> 503 DATABASE_CONNECTION_LOST`
- `IntegrityError -> 409 DATABASE_CONFLICT`
- `DataError -> 400 DATABASE_INVALID_DATA`
- `DatabaseError -> 503 DATABASE_ERROR`

目标：

- 前端永远拿到结构化错误。
- 日期类型错误不再造成全局 500。
- Supabase pooler 短暂不可用时表现为可恢复失败。

### 回归测试

文件：

- `backend/tests/test_sprint4_infra.py`
- `scripts/test_product_stability.ps1`

已覆盖：

- 数据库连接初始化会设置 timeout。
- Supabase 断连类异常返回可恢复 JSON。
- 日期/类型错误返回 `400 DATABASE_INVALID_DATA`。
- 产品稳定性脚本默认纳入数据库异常处理测试。

## P0 优化任务

### P0-1 移除请求路径中的运行时 DDL

#### 问题

当前部分路由仍会在用户请求中执行：

- `ALTER TABLE plans ADD COLUMN IF NOT EXISTS ...`
- `ALTER TABLE nodes ADD COLUMN IF NOT EXISTS ...`
- `ALTER TABLE plans DROP CONSTRAINT ...`
- `ALTER TABLE plans ADD CONSTRAINT ...`

这些 DDL 会产生锁等待。在 Supabase 上，如果请求高峰或连接池状态不佳，运行时 DDL 可能导致普通用户接口变慢、超时或失败。

#### 目标

所有 schema 变更必须迁移到离线 migration，不允许用户请求执行 DDL。

#### AI Coding Steps

1. 扫描所有运行时 DDL：
   - `backend/routers/plans.py`
   - `backend/routers/graph.py`
   - `backend/routers/ai.py`
   - `backend/scripts`
2. 创建新的 migration SQL：
   - `backend/sql/2026-05-16_supabase_runtime_ddl_cleanup.sql`
3. 将以下字段/约束写入 migration：
   - `plans.start_date`
   - `plans.target_end_date`
   - `plans.study_frequency`
   - `plans.study_days_per_week`
   - `plans.reminder_enabled`
   - `plans.reminder_time`
   - `plans.reminder_timezone`
   - `plans.archived_reason`
   - `nodes.target_end_date`
   - `nodes.resource_search_cache`
   - `plans_status_check`
4. 将 `_ensure_plan_management_columns` 和 `_ensure_node_management_columns` 改为轻量 schema readiness check，或在生产环境直接 no-op。
5. 保留开发环境下的明确错误提示：如果字段缺失，返回 `SCHEMA_NOT_READY`，提示先执行 migration。

#### Acceptance Criteria

- `rg "ALTER TABLE" backend/routers backend/services` 不再出现用户请求路径 DDL。
- 计划列表、图谱加载、节点截止日期、资源搜索不再触发 DDL。
- migration 可重复执行。
- 字段缺失时返回结构化错误，不白屏、不崩溃。

#### Tests

- 新增 `backend/tests/unit/test_schema_readiness.py`
- 模拟字段缺失，确认返回 `503 SCHEMA_NOT_READY`。
- 运行：

```powershell
python -m pytest tests\unit\test_schema_readiness.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -SkipBuild
```

### P0-2 增加事务 helper，统一 rollback/commit 边界

#### 问题

多步写入接口依赖请求结束时连接释放 rollback，但代码层面的事务边界不够显式。典型接口：

- 创建计划：插入 plans、nodes、edges。
- 更新节点状态：更新 node、plan progress、learning_sessions、user_profiles。
- 应用图谱变更：删除节点、添加节点、更新标题、重算进度。
- 笔记创建：校验 plan/node 后插入 note。

#### 目标

所有多步写入使用统一事务上下文。任何一步失败，明确 rollback，绝不留下半成品状态。

#### AI Coding Steps

1. 在 `backend/database.py` 增加：

```python
@contextmanager
def transaction(db):
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
```

2. 改造多步写入接口：
   - `create_plan`
   - `update_node_status`
   - `update_nodes_positions`
   - `apply_changes`
   - `create_note`
   - `update_note`
   - `delete_note`
3. 去掉中间散落的 `db.commit()`，统一由 transaction 管理。
4. 对只读接口不引入事务 helper。

#### Acceptance Criteria

- 多步写入失败不会部分落库。
- 重复点击写入失败后，刷新页面不会出现半条 plan、孤儿 nodes、孤儿 edges。
- 所有事务失败都返回结构化错误。

#### Tests

- 新增 `backend/tests/unit/test_database_transaction.py`
- 新增/扩展集成测试：
  - 创建计划中途插入 node 失败，plans 不应残留。
  - 更新节点状态时 learning_sessions 失败，node status 不应变更。
  - apply changes 中途失败，nodes/title/progress 不应半更新。

### P0-3 前端数据库失败不清空页面状态

#### 问题

有些前端 action 在 API 失败后可能进入不一致状态：

- 乐观更新成功但服务端失败。
- 加载失败后用空数组覆盖旧数据。
- 保存失败后按钮状态停留或用户输入丢失。

#### 目标

Supabase 请求失败时，前端保持最近一次可用状态，并显示可恢复错误。

#### AI Coding Steps

1. 审查以下文件：
   - `frontend/src/contexts/PlanContext.jsx`
   - `frontend/src/contexts/NoteContext.jsx`
   - `frontend/src/pages/HomePage.jsx`
   - `frontend/src/pages/GraphPage.jsx`
   - `frontend/src/pages/MyLearningPage.jsx`
2. 为核心数据增加 stale-cache 策略：
   - plans cache
   - graph cache by plan id
   - notes cache
3. API 失败时：
   - 不用空数组覆盖旧状态。
   - 不关闭用户正在编辑的 modal。
   - 不清空用户输入。
   - 明确 toast 或 inline error。
4. 对乐观更新增加 rollback：
   - 节点截止日期保存失败时恢复旧日期。
   - 节点状态更新失败时恢复旧状态。
   - 计划 deadline 更新失败时恢复旧 plan。

#### Acceptance Criteria

- Supabase 503 时，用户仍能看到最近一次成功加载的数据。
- 截止日期保存失败不会显示成已保存。
- 图谱加载失败不会让整个图谱页清空。
- 笔记加载失败仍可显示本地缓存。

#### Tests

- 前端单测：
  - `PlanContext` list failure fallback。
  - `GraphPage` node deadline save failure rollback。
  - `HomePage` plan update failure rollback。
  - `NoteContext` cached notes fallback。

## P1 优化任务

### P1-1 节点位置更新防抖和批量保存

#### 问题

拖拽节点时如果频繁保存位置，可能打满 Supabase 连接池或产生大量无意义写入。

#### 目标

拖拽过程只更新前端状态，拖拽结束后批量保存，失败时不阻塞 UI。

#### AI Coding Steps

1. 检查 `frontend/src/pages/GraphPage.jsx` 和 graph interaction hook。
2. 将连续位置更新合并为 debounce/batch：
   - debounce 500ms。
   - 或只在 pointer up / drag end 后调用 `/nodes/positions`。
3. 后端 `update_nodes_positions` 增加单事务处理。
4. 前端失败时标记“布局未同步”，允许用户再次保存。

#### Acceptance Criteria

- 连续拖拽 10 秒不会产生几十/上百个 Supabase 请求。
- 位置保存失败不影响节点学习、AI 解释、笔记功能。

### P1-2 请求幂等键

#### 问题

用户刷新、重复点击或网络重试时，可能重复创建笔记、重复写 learning session、重复执行 AI 结果保存。

#### 目标

关键写入接口支持 idempotency key，同一用户同一 key 只执行一次。

#### AI Coding Steps

1. 新增表：

```sql
CREATE TABLE IF NOT EXISTS idempotency_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  response JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

2. 前端为以下动作生成 key：
   - AI 解释保存为笔记。
   - 聊天总结保存为笔记。
   - 手动创建笔记。
   - 节点状态更新。
3. 后端读取 `Idempotency-Key` header：
   - key 已存在则直接返回缓存 response。
   - key 不存在则执行写入并保存 response。
4. 增加 TTL 清理策略，保留 24-72 小时。

#### Acceptance Criteria

- 同一个保存笔记请求重复发送，不会创建两条笔记。
- 刷新后重试不会重复记录学习 session。
- 幂等缓存失败不影响主流程，但必须有日志。

### P1-3 Supabase 健康检查和降级状态

#### 问题

当前 `/health` 只返回应用健康，不检查 Supabase。前端无法判断“服务活着但数据库不可用”。

#### 目标

增加数据库健康检查和前端降级提示。

#### AI Coding Steps

1. 新增：
   - `GET /health`
   - `GET /health/db`
2. `/health/db` 执行短超时 `SELECT 1`。
3. 返回：

```json
{
  "status": "ok|degraded",
  "database": "ok|unavailable",
  "latencyMs": 12
}
```

4. 前端启动时或请求失败后可选调用 health db。
5. 如果数据库不可用，显示“数据同步暂时不可用，本地内容仍可查看”。

#### Acceptance Criteria

- Supabase 不可用时 `/health` 仍可返回 app alive。
- `/health/db` 明确返回 degraded。
- 前端不会误判为整个应用挂了。

## P2 优化任务

### P2-1 API 错误码前端统一映射

#### 问题

现在 `fetchApi` 只抛普通 `Error`，前端很多地方只能拿 message，无法基于 code 做恢复策略。

#### 目标

前端错误对象携带：

- `status`
- `code`
- `message`
- `endpoint`
- `recoverable`

#### AI Coding Steps

1. 在 `frontend/src/services/api.js` 新增 `ApiError`。
2. `fetchApi` 解析错误时抛 `ApiError`。
3. 约定 recoverable：
   - `DATABASE_UNAVAILABLE`
   - `DATABASE_CONNECTION_LOST`
   - `DATABASE_ERROR`
   - `RATE_LIMITED`
4. 页面根据 `error.recoverable` 决定保留状态、显示重试。

#### Acceptance Criteria

- 前端可以区分“数据格式错误”和“Supabase 暂时不可用”。
- 所有 toast/inline error 不再只显示模糊的 `API Error`。

落地状态（2026-05-16）：

- 已新增 `apiErrorMessages`，统一区分 recoverable 数据库错误和不可恢复业务错误。
- AppContext 已汇总 plans/notes 的 recoverable load error，输出 `dataSyncStatus`。
- 已新增全局数据同步降级提示，Supabase 暂时不可用时提示“本地内容仍可查看”。
- 已将 `apiErrorMessages.test.js` 纳入 `scripts/test_product_stability.ps1` 默认稳定性门禁。

### P2-2 上线观测指标

#### 目标

上线后可以看出 Supabase 是否在拖慢产品。

#### Metrics

- `/api/plans` P50/P95/P99 latency。
- `/api/plans/{id}/graph` P50/P95/P99 latency。
- `/api/notes` error rate。
- `DATABASE_UNAVAILABLE` count。
- `DATABASE_INVALID_DATA` count。
- connection pool acquire failure count。
- lock timeout count。
- statement timeout count。

#### AI Coding Steps

1. 后端 middleware 记录 endpoint、status、duration。
2. 数据库异常 handler 记录 code 和 endpoint。
3. 先输出结构化日志，后续可接入 Supabase logs / Sentry / OpenTelemetry。

## 自动化测试矩阵

### Backend Unit

```powershell
python -m pytest tests\test_sprint4_infra.py tests\unit\test_graph_deadline_validation.py -q
```

覆盖：

- 数据库 timeout 配置。
- 数据库异常结构化响应。
- 截止日期格式和过去日期校验。

### Backend Integration

```powershell
python -m pytest tests\test_notes_crud.py tests\test_graph.py tests\test_plan_management_api.py tests\test_recommend_next_api.py -q
```

覆盖：

- 真实 Supabase CRUD。
- 计划/节点/笔记权限边界。
- 节点截止日期持久化。
- 推荐节点接口数据库读取。

### Frontend Unit

```powershell
npm run test:unit -- AppContext.sprint4.test.jsx HomePage.recommendation.test.jsx noteCapture.test.js aiRequestRegistry.test.js api.sprint3.test.js
```

覆盖：

- 缓存兜底。
- AI 请求取消。
- 失败不清空状态。
- API 错误解析。

### Product Stability Gate

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1
```

上线前完整检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_product_stability.ps1 -IncludeDbIntegration -IncludeE2E
```

## 推荐实施顺序

### Phase 1 - Schema 和事务稳定

1. 移除请求路径 DDL。
2. 新增 migration。
3. 增加 transaction helper。
4. 改造多步写入接口。
5. 增加 rollback 测试。

### Phase 2 - 前端失败隔离

1. `ApiError` 标准化。
2. plans/graph/notes stale-cache。
3. 截止日期、节点状态、笔记保存失败 rollback。
4. 增加连续点击和失败恢复测试。

### Phase 3 - 幂等和压力控制

1. 节点位置保存防抖/批量。
2. 写接口 idempotency key。
3. 重复点击/刷新后重试自动化测试。

### Phase 4 - 观测和上线门禁

1. `/health/db`。
2. 结构化日志。
3. 数据库错误指标。
4. 完整 DB integration + Playwright gate。

落地状态（2026-05-16）：

- 已新增 `/health/db`，数据库不可用时返回 degraded，不影响 `/health` 应用存活检查。
- 已新增 `/health/metrics`，输出请求计数、错误计数、平均/最大延迟和数据库错误计数。
- 已增加结构化请求日志和 `X-Request-ID` 响应头。
- 已将观测模块纳入 `scripts/test_product_stability.ps1` 默认稳定性门禁。
- 已保留 `-IncludeDbIntegration -DeepDbIntegration -IncludeE2E` 作为发布前慢速完整门禁。

## Definition of Done

- Supabase 断连时，产品仍显示最近一次可用数据。
- 任意一个写接口失败，不会清空页面状态。
- 多步写入失败不会产生半成品数据。
- 用户连续点击不会重复创建笔记或重复记录学习 session。
- 运行时 DDL 不再出现在用户请求路径。
- 所有数据库异常都有结构化错误码。
- 默认稳定性测试和完整上线前测试均通过。
