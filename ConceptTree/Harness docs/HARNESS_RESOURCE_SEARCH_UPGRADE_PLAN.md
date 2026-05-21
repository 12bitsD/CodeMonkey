# ConceptTree - Harness Engineering 更新计划
## 推荐资源“搜索更多”升级

> 生成日期：2026-04-17  
> 范围：知识节点详情抽屉中的“推荐资源”区域

---

## 目标

为每个知识节点的“推荐资源”增加一个“搜索更多资源”按钮，接入联网搜索，并确保新增资源在以下情况下不会丢失：

- 关闭详情抽屉
- 退出当前画布页
- 刷新页面
- 重新进入该学习计划

这次升级的核心不是单纯把搜索结果展示出来，而是把“资源扩展结果”纳入现有图谱数据模型，变成可持久化、可恢复、可测试的正式状态。

---

## Harness 核心原则

```text
Harness = 明确入口
        + 单一持久化通道
        + 读取时自动恢复
        + 不覆盖已有资源
        + 有测试闭环
```

本次功能必须满足：

1. 用户触发入口唯一：节点详情内的“搜索更多资源”按钮。
2. 搜索结果不只停留在前端 state，必须落盘到后端。
3. 页面重新加载后，前端能从 graph 接口自动恢复扩展资源状态。
4. 不能破坏现有 `resources` 的初始推荐结果。
5. 搜索失败、重复搜索、重复资源，都要有守门逻辑。

---

## 现状判断

当前可复用的基础已经具备：

- 节点已有 `resources` 字段，前端会通过 graph 接口拿到资源列表。
- 后端已经有 `SearchService`，可以复用联网搜索能力。
- 前端图谱页已有 `GraphContext` 缓存，可减少重复请求。
- 节点解释缓存 `content_cache` 已有“生成 -> 后端持久化 -> 刷新恢复”的成熟模式。

结论：

- 这次最适合沿用“内容缓存”思路，为资源扩展增加独立持久化字段。
- 不建议直接把联网搜索得到的内容无脑覆盖原始 `resources`。

---

## 推荐方案

### 数据模型

为 `nodes` 增加一个新的 JSONB 字段，建议命名：

- `resource_search_cache`

结构建议：

```json
{
  "items": [
    {
      "name": "反向传播详解",
      "url": "https://example.com",
      "reason": "补充数学推导",
      "source": "web_search"
    }
  ],
  "query": "反向传播 学习教程",
  "updatedAt": "2026-04-17T23:30:00Z"
}
```

设计原因：

- 与原始 `resources` 分离，避免覆盖模型生成结果。
- 能记录搜索词和更新时间，便于后续加“重新搜索”或“最近更新”提示。
- 前端恢复时更清晰，测试也更容易写。

### Graph 接口输出

`GET /api/plans/{plan_id}/graph` 在节点序列化时增加：

- `resourceSearchCache`

前端收到后，展示时使用：

```text
displayResources = [...resources, ...resourceSearchCache.items]
```

同时对 URL 做去重，避免同一链接重复出现。

### 搜索入口

在节点详情页推荐资源区域增加按钮：

- 默认文案：`搜索更多资源`
- 搜索中：`搜索中...`
- 已有缓存时：`查看更多资源`

交互顺序：

1. 点击按钮
2. 调用后端资源搜索接口
3. 后端搜索并写入 `resource_search_cache`
4. 前端更新当前节点和 `GraphContext`
5. 用户刷新后仍可看到新增资源

---

## 代码改动计划

### Backend

#### 1. 数据库

新增 migration / schema 更新：

- `backend/schema.sql`
- `backend/sql/..._add_resource_search_cache.sql`

字段：

- `resource_search_cache JSONB DEFAULT '{}'::jsonb`

#### 2. 模型

更新：

- `backend/models.py`

新增字段：

- `resourceSearchCache: Dict[str, Any] = {}`

如需单独接口请求体，可增加：

- `ResourceSearchRequest`
- `ResourceSearchResponse`

#### 3. Graph 序列化

更新：

- `backend/routers/graph.py`

在节点返回里增加：

- `resourceSearchCache`

#### 4. 新增资源搜索接口

建议位置：

- `backend/routers/ai.py` 或 `backend/routers/graph.py`

推荐接口：

`POST /api/graph/{plan_id}/nodes/{node_id}/search-resources`

请求体：

```json
{
  "query": "反向传播 学习教程"
}
```

职责：

- 读取当前节点
- 生成默认搜索词
- 调用 `SearchService`
- 将结果映射为资源卡片结构
- 去重后写入 `resource_search_cache`
- 返回最新缓存

#### 5. 搜索映射规则

搜索结果落成统一结构：

```python
{
  "name": result["title"],
  "url": result["url"],
  "reason": result["snippet"],
  "source": "web_search",
}
```

守门要求：

- 丢弃无标题或无 URL 的结果
- 同域名结果数量可加上限
- 对同一 URL 去重
- 限制返回数量，比如最多 6 条

### Frontend

#### 1. 资源区域 UI

更新：

- `frontend/src/components/node/ResourceList.jsx`
- `frontend/src/pages/GraphPage.jsx`

新增：

- “搜索更多资源”按钮
- 搜索中的 loading 状态
- 扩展资源分组标识，例如“小标签：联网搜索”

#### 2. 节点资源合并逻辑

在 `GraphPage.jsx` 中合并：

- `selectedNode.resources`
- `selectedNode.resourceSearchCache?.items`

要求：

- URL 去重
- 原始推荐资源优先显示
- 搜索资源追加在后面

#### 3. 本地状态同步

搜索成功后同时更新：

- `nodes`
- `GraphContext`

这样即使不重新拉 graph，本次 session 也能即时看到结果。

#### 4. 页面重载恢复

依赖 graph 接口返回的 `resourceSearchCache` 自动恢复，无需额外前端缓存。

---

## 用户体验细节

### 按钮状态

- 无缓存：`搜索更多资源`
- 搜索中：`搜索中...`
- 有缓存：`查看更多资源`

### 资源来源展示

扩展资源建议在卡片上加轻量来源标识：

- `联网搜索`

### 错误提示

- 搜索失败：`资源搜索失败，请重试`
- 无结果：`暂未找到更多高质量资源`

---

## 风险与守门

### 风险 1 - 覆盖原始资源

守门：

- 新增独立字段 `resource_search_cache`
- 不直接覆写 `resources`

### 风险 2 - 刷新后丢失

守门：

- 结果必须写入数据库
- graph 接口必须回传缓存字段

### 风险 3 - 重复资源

守门：

- 后端按 URL 去重
- 前端合并展示时再次按 URL 去重

### 风险 4 - 搜索结果质量不稳定

守门：

- 限制结果数
- 可选允许域名白名单
- 优先使用标题 + 摘要明确的结果

---

## Harness Hooks 建议

### Hook A - 资源持久化守门

当修改以下文件时提醒检查：

- `backend/routers/graph.py`
- `backend/models.py`
- `frontend/src/pages/GraphPage.jsx`

检查项：

- 搜索结果是否真的写入后端
- graph 接口是否真的把缓存字段返回前端

### Hook B - 去重守门

当修改资源映射逻辑时自动检查：

- 是否按 URL 去重
- 是否仍保留原始 `resources`

### Hook C - 前端恢复守门

当修改资源显示逻辑时自动检查：

- 页面初次加载是否能从节点数据直接恢复扩展资源

---

## 测试计划

### Backend

新增测试建议：

- `backend/tests/test_resource_search_api.py`
- `backend/tests/test_graph_resource_cache.py`

覆盖点：

- 搜索结果能写入 `resource_search_cache`
- graph 接口返回 `resourceSearchCache`
- 同 URL 结果去重
- 搜索失败时不破坏原资源

### Frontend

新增测试建议：

- `frontend/src/components/node/ResourceList.search.test.jsx`
- `frontend/src/pages/GraphPage.resource-search.test.jsx`

覆盖点：

- 点击按钮后显示 loading
- 搜索成功后展示扩展资源
- 扩展资源和原资源合并显示
- 页面从 graph 数据恢复扩展资源

### 脚本

建议新增：

- `scripts/test_resource_search_upgrade.ps1`

建议执行：

```powershell
Push-Location "$PSScriptRoot\..\backend"
python -m pytest tests/test_resource_search_api.py -q
python -m pytest tests/test_graph_resource_cache.py -q
Pop-Location

Push-Location "$PSScriptRoot\..\frontend"
npx vitest run src/components/node/ResourceList.search.test.jsx src/pages/GraphPage.resource-search.test.jsx --pool=threads
npx eslint src/pages/GraphPage.jsx src/components/node/ResourceList.jsx src/services/api.js
Pop-Location
```

---

## 验收标准

满足以下条件才算完成：

1. 节点详情中能点击“搜索更多资源”。
2. 搜索完成后新资源会显示在推荐资源区域。
3. 用户关闭详情、退出画布、刷新页面后，新资源仍然存在。
4. 原始推荐资源不会被覆盖。
5. 同一资源不会重复出现。
6. 相关前后端测试和脚本可通过。

---

## 实施顺序

1. 后端加字段与 graph 返回
2. 后端新增资源搜索接口
3. 前端接入按钮与 loading
4. 前端做资源合并与恢复
5. 加测试和脚本
6. 手工验证刷新/重进恢复
