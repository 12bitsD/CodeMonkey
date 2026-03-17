# ConceptTree Phase 6-8 设计文档：补完 MVP

**日期**: 2026-03-17  
**状态**: 设计中  
**目标**: 补齐 MVP 未完成的功能缺口

---

## 背景

Phase 1-5 已完成核心功能：
- ✅ 用户认证、计划 CRUD、图谱可视化
- ✅ AI 解析目标、生成图谱、clarify-goal
- ✅ 节点状态/位置持久化、全局 Toast
- ✅ 测试基础设施（Vitest + Playwright）

但 MVP 仍有功能缺口未实现，影响用户体验。

---

## 缺口盘点

| 优先级 | 功能 | 当前状态 | 目标 |
|--------|------|----------|------|
| 🔴 P0 | 掌握标准 & 推荐资源展示 | 后端生成并存储，前端未展示 | GraphPage 节点详情面板完整展示 |
| 🟡 P1 | 笔记按计划分组筛选 | 平铺列表，无筛选 | 下拉选择计划，分组显示 |
| 🟡 P1 | 笔记跳转精准定位 | 只跳转到图谱页 | 跳转到具体节点并高亮 |
| 🟡 P1 | 首页进度实时同步 | 图谱页学习后首页不刷新 | 进度自动更新 |
| 🟢 P2 | Token 黑名单 | logout 只删前端 token | 后端黑名单机制 |

---

## Phase 6: 节点详情完善 (Node Detail Enhancement)

### 目标
补齐 mastery & resources 在 GraphPage 的展示。

### 技术事实
- 后端 `models.py` 已有 `mastery: List[str]` 和 `resources: List[Resource]`
- `generate_graph.json` prompt 要求 AI 生成这两个字段
- 数据库 `schema.sql` 已存储为 JSONB
- 当前 GraphPage 侧边栏只展示 why/what/prompt/notes

### 任务分解（TDD）

#### Task 1: 验证后端数据完整性
**RED**: 编写测试验证 `/api/plans/{id}/graph` 返回包含 mastery/resources
```python
def test_graph_response_includes_mastery_and_resources():
    response = client.get("/api/plans/p1/graph")
    node = response.json()["data"]["nodes"][0]
    assert "mastery" in node
    assert "resources" in node
    assert isinstance(node["mastery"], list)
    assert isinstance(node["resources"], list)
```

**GREEN**: 确认现有代码已返回（无需修改）

#### Task 2: 掌握标准组件
**RED**: 编写 E2E 测试验证掌握标准显示
```javascript
test('node detail shows mastery checklist', async ({ page }) => {
  await page.goto('/graph/p1');
  await page.click('[data-testid="node-n1"]');
  await expect(page.locator('[data-testid="mastery-section"]')).toBeVisible();
  await expect(page.locator('[data-testid="mastery-item"]')).toHaveCount.greaterThan(0);
});
```

**GREEN**: 创建 `MasteryChecklist.jsx` 组件
```jsx
// components/node/MasteryChecklist.jsx
export function MasteryChecklist({ items }) {
  if (!items?.length) return null;
  return (
    <section data-testid="mastery-section">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-4">
        掌握标准
      </h4>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3">
            <input type="checkbox" className="mt-1" />
            <span className="text-sm text-zinc-600">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

#### Task 3: 推荐资源组件
**RED**: 编写 E2E 测试验证资源链接可点击
```javascript
test('node detail shows resources with links', async ({ page }) => {
  await page.click('[data-testid="node-n1"]');
  await expect(page.locator('[data-testid="resource-link"]')).toBeVisible();
});
```

**GREEN**: 创建 `ResourceList.jsx` 组件
```jsx
// components/node/ResourceList.jsx
export function ResourceList({ resources }) {
  if (!resources?.length) return null;
  return (
    <section data-testid="resources-section">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-4">
        推荐资源
      </h4>
      <div className="space-y-3">
        {resources.map((r, i) => (
          <a
            key={i}
            href={r.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="resource-link"
            className="block p-3 bg-zinc-50 rounded-lg hover:bg-zinc-100 transition-colors"
          >
            <div className="font-medium text-sm text-zinc-800">{r.name}</div>
            {r.reason && (
              <div className="text-xs text-zinc-500 mt-1">{r.reason}</div>
            )}
          </a>
        ))}
      </div>
    </section>
  );
}
```

#### Task 4: GraphPage 集成
**文件**: `frontend/src/pages/GraphPage.jsx`

在侧边栏插入新组件（在 prompt 和 notes 之间）：
```jsx
{selectedNode.mastery?.length > 0 && (
  <MasteryChecklist items={selectedNode.mastery} />
)}

{selectedNode.resources?.length > 0 && (
  <ResourceList resources={selectedNode.resources} />
)}
```

### 验收标准
- [ ] GraphPage 节点详情显示「掌握标准」可勾选列表
- [ ] GraphPage 节点详情显示「推荐资源」带链接卡片
- [ ] E2E 测试通过
- [ ] 移动端样式正常

---

## Phase 7: 笔记体验优化 (Notes Experience)

### 目标
笔记 Tab 支持分组、筛选、精准跳转。

### 当前问题
- 笔记平铺显示，无计划分组
- 无法按计划筛选
- 点击笔记只跳转到图谱页，不定位到具体节点

### 任务分解（TDD）

#### Task 1: 笔记数据增强
**RED**: 测试笔记包含 nodeId 用于跳转
```javascript
test('notes include nodeId for navigation', async ({ page }) => {
  const notes = await page.evaluate(() => window.__notesData);
  expect(notes[0]).toHaveProperty('nodeId');
  expect(notes[0]).toHaveProperty('planId');
});
```

**注意**: 检查后端 `notes` 表和 API 是否返回 `node_id`，如无需要 migration。

#### Task 2: 计划筛选器组件
**RED**: E2E 测试筛选功能
```javascript
test('can filter notes by plan', async ({ page }) => {
  await page.goto('/my-learning');
  await page.click('[data-testid="notes-tab"]');
  await page.selectOption('[data-testid="plan-filter"]', 'p1');
  await expect(page.locator('[data-testid="note-item"]')).toHaveCount(2);
});
```

**GREEN**: 创建筛选 UI
```jsx
// MyLearningPage Notes Tab
const [selectedPlan, setSelectedPlan] = useState('all');

<div className="flex gap-4 mb-6">
  <select 
    data-testid="plan-filter"
    value={selectedPlan}
    onChange={e => setSelectedPlan(e.target.value)}
    className="px-4 py-2 bg-zinc-50 rounded-lg text-sm"
  >
    <option value="all">全部计划</option>
    {plans.map(p => (
      <option key={p.id} value={p.id}>{p.title}</option>
    ))}
  </select>
</div>

{filteredNotes.map(note => (
  <div 
    key={note.id}
    data-testid="note-item"
    onClick={() => navigate(`/graph/${note.planId}?node=${note.nodeId}`)}
  >
    {/* ... */}
  </div>
))}
```

#### Task 3: 按计划分组展示
**GREEN**: 分组渲染
```jsx
const notesByPlan = groupBy(filteredNotes, 'planId');

{Object.entries(notesByPlan).map(([planId, notes]) => (
  <div key={planId} className="mb-8">
    <h3 className="text-sm font-medium text-zinc-500 mb-4">
      {getPlanTitle(planId)}
    </h3>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {notes.map(note => <NoteCard key={note.id} note={note} />)}
    </div>
  </div>
))}
```

#### Task 4: URL 路由支持 node 参数
**文件**: `frontend/src/App.jsx` 或路由配置

无需修改路由定义，GraphPage 读取 query param：
```jsx
// GraphPage.jsx
import { useSearchParams } from 'react-router-dom';

const [searchParams] = useSearchParams();
const highlightNodeId = searchParams.get('node');

useEffect(() => {
  if (highlightNodeId && nodes.length > 0) {
    setSelectedNodeId(highlightNodeId);
    // 可选：滚动到该节点
  }
}, [highlightNodeId, nodes]);
```

### 验收标准
- [ ] 笔记 Tab 显示计划筛选下拉框
- [ ] 笔记按计划分组显示
- [ ] 点击笔记跳转到图谱页并自动选中对应节点
- [ ] E2E 测试通过

---

## Phase 8: 进度实时同步 (Progress Sync)

### 目标
图谱页学习进度变更后，首页计划卡片自动更新。

### 当前问题
- GraphPage 标记节点已学 → 调用 API 更新后端
- 回到 HomePage，计划卡片进度仍是旧值（需刷新才更新）

### 方案对比

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| A: Context 同步 | 即时更新，无需请求 | 需修改全局状态逻辑 | ⭐ 推荐 |
| B: SWR/React Query | 自动刷新，缓存策略 | 引入新依赖 | 次选 |
| C: 轮询/WebSocket | 真正的实时 | 过度设计 | 不推荐 |

### 任务分解（TDD）

#### Task 1: 进度计算工具函数
**RED**: 单元测试
```javascript
// utils/progress.test.js
test('calculateProgress excludes skipped nodes', () => {
  const nodes = [
    { id: 'n1', status: 'learned' },
    { id: 'n2', status: 'unlearned' },
    { id: 'n3', status: 'skipped' },
  ];
  expect(calculateProgress(nodes)).toEqual({ learned: 1, total: 2 });
});
```

**GREEN**: 实现
```javascript
export const calculateProgress = (nodes) => {
  const relevant = nodes.filter(n => n.status !== 'skipped');
  const learned = relevant.filter(n => n.status === 'learned').length;
  return { learned, total: relevant.length };
};
```

#### Task 2: Context 状态同步
**文件**: `frontend/src/contexts/AppContext.jsx`

当前 `actions.updateNodeStatus` 只更新 plan，需要同时更新 plans 列表中的进度：
```javascript
const updateNodeStatus = async (planId, nodeId, status) => {
  // 调用 API
  await graphApi.updateNodeStatus(planId, nodeId, status);
  
  // 更新本地 plan 状态（已存在）
  setPlans(prev => prev.map(plan => {
    if (plan.id !== planId) return plan;
    
    // 更新节点状态
    const updatedNodes = plan.nodes.map(n => 
      n.id === nodeId ? { ...n, status } : n
    );
    
    // 重新计算进度
    const { learned, total } = calculateProgress(updatedNodes);
    
    return {
      ...plan,
      nodes: updatedNodes,
      progress: learned,
      total
    };
  }));
};
```

#### Task 3: HomePage 订阅更新
**文件**: `frontend/src/pages/HomePage.jsx`

确保使用最新 plans 数据：
```javascript
// 当前使用 plans 来自 AppContext，已自动更新
// 只需确保渲染使用 plans，而非本地缓存
const { plans } = useAppContext();

// 计划卡片直接使用 plan.progress / plan.total
```

#### Task 4: E2E 测试
```javascript
test('progress syncs from graph page to home page', async ({ page }) => {
  // 1. 进入图谱页，记录当前进度
  await page.goto('/graph/p1');
  await page.click('[data-testid="node-n1"]');
  
  // 2. 标记已学
  await page.click('[data-testid="mark-learned-btn"]');
  
  // 3. 回到首页
  await page.click('[data-testid="back-home"]');
  
  // 4. 验证进度已更新
  await expect(page.locator('[data-testid="plan-card-progress"]')).toHaveText('1/7');
});
```

### 验收标准
- [ ] 图谱页标记节点后，首页卡片进度即时更新（无需刷新）
- [ ] E2E 测试通过
- [ ] 移动端表现一致

---

## 实施顺序

```
Phase 6 (P0) → Phase 7 (P1) → Phase 8 (P1)
     ↓              ↓              ↓
  2-3 天        2-3 天         1-2 天
```

**理由**:
- Phase 6 是核心功能缺失，直接影响用户判断学习成果
- Phase 7 提升笔记管理效率
- Phase 8 是体验优化，可并行或延后

---

## 附录：代码位置参考

| 组件/功能 | 文件路径 |
|-----------|----------|
| GraphPage 侧边栏 | `frontend/src/pages/GraphPage.jsx:331-448` |
| MyLearningPage | `frontend/src/pages/MyLearningPage.jsx:231-270` |
| AppContext | `frontend/src/contexts/AppContext.jsx` |
| HomePage 计划卡片 | `frontend/src/pages/HomePage.jsx` |
| 后端 graph API | `backend/routers/graph.py` |
| 后端 notes API | `backend/routers/notes.py` |
| E2E 测试 | `frontend/tests/main-flow.spec.js` |

---

*设计完成时间: 2026-03-17*
*下一步: 用户确认 → 编写 Implementation Plan*
