# ConceptTree Phase 6-10 重新规划：补全 MVP 缺口

**日期**: 2026-03-17  
**基于**: PRD 全面梳理结果  
**目标**: 补全所有 MVP 未完成功能

---

## 背景：梳理发现的缺口

### AI 方向（3个核心缺口）

| 功能 | 当前状态 | PRD 要求 | 差距 |
|------|---------|---------|------|
| **recommend-next 后端** | 前端规则引擎 | AI基于图谱+画像+历史智能推荐 | 🔴 大 |
| **apply-changes 后端** | 跳转首页新建 | 根据clarify结果修改现有图谱 | 🔴 大 |
| **学习历史用于 AI** | 有表但未使用 | AI推荐时输入学习历史 | 🟡 中 |

### 前端展示（7个缺口）

| 功能 | 当前状态 | PRD 要求 | 差距 |
|------|---------|---------|------|
| **掌握标准展示** | ❌ 未展示 | 节点卡片显示mastery checklist | 🔴 大 |
| **推荐资源展示** | ❌ 未展示 | 节点卡片显示resources链接 | 🔴 大 |
| **"搜索更多资源"按钮** | ❌ 未实现 | Google搜索跳转 | 🟡 中 |
| **笔记删除** | ❌ 未实现 | 可删除笔记 | 🟡 中 |
| **笔记分组筛选** | ❌ 未实现 | 按计划分组+下拉筛选 | 🟡 中 |
| **笔记精准跳转** | ⚠️ 部分 | 跳转到具体节点并高亮 | 🟡 中 |
| **进度实时同步** | ❌ 未实现 | 图谱页学习后首页自动刷新 | 🟡 中 |

### 用户画像（4个缺口）

| 功能 | 当前状态 | PRD 要求 | 差距 |
|------|---------|---------|------|
| **编程/数学基础下拉** | ❌ 未实现 | MyLearningPage下拉选择 | 🟡 中 |
| **已掌握知识自动汇总** | ⚠️ 部分 | 从学习记录自动汇总 | 🟡 中 |
| **画像摘要实时分析** | ❌ 未实现 | 首页显示"已知背景" | 🟢 低 |
| **首页画像用途** | ⚠️ 部分 | 根据画像调整生成 | 🟢 低 |

### 其他（3个缺口）

| 功能 | 当前状态 | PRD 要求 | 差距 |
|------|---------|---------|------|
| **"用于"链接跳转** | ❌ 未实现 | 点击跳转到目标节点 | 🟢 低 |
| **双击切换状态** | ❌ 未实现 | 双击节点快速切换状态 | 🟢 低 |

---

## Phase 6: AI recommend-next 后端

### 目标
实现真正的 AI 学习调度，替代前端规则引擎。

### PRD 要求（492-530行）

**输入**：
```json
{
  "graph": { "nodes": [...], "edges": [...], "target_node_id": "5" },
  "user_profile": { "occupation": "...", "abilities": [...], "mastered_knowledge": [...] },
  "learning_history": { "last_node": "...", "last_session": "...", "learned_nodes": [...] },
  "learning_goal": "..."
}
```

**输出**：
```json
{
  "recommended_node_id": "2",
  "reason": "链式法则是通往反向传播的关键路径，且你已完成前置的矩阵乘法"
}
```

### 当前前端规则引擎（useGraphInteraction.js:22-29）
```javascript
const recommendedNode = useMemo(() => {
  return nodes.find(n => 
    n.status === 'unlearned' && 
    edges.filter(e => e.to === n.id)
      .every(e => nodes.find(fn => fn.id === e.from)?.status !== 'unlearned')
  );
}, [nodes, edges]);
```

### Task 1: 数据库 - 学习历史聚合

**RED**: 测试获取用户学习历史
```python
def test_get_learning_history():
    history = get_learning_history(user_id="u1", plan_id="p1")
    assert "last_node" in history
    assert "learned_nodes" in history
    assert "skipped_nodes" in history
```

**GREEN**: 实现查询函数
```python
# services/learning_history.py
async def get_learning_history(user_id: str, plan_id: str, db) -> dict:
    """获取用户学习历史，用于AI推荐"""
    # 最后学习的节点
    last_session = await db.fetchone(
        """SELECT node_id, node_name, created_at 
           FROM learning_sessions 
           WHERE user_id = ? AND plan_id = ? 
           ORDER BY created_at DESC LIMIT 1""",
        (user_id, plan_id)
    )
    
    # 已学和跳过的节点
    learned = await db.fetch(
        """SELECT DISTINCT node_id FROM learning_sessions 
           WHERE user_id = ? AND plan_id = ? AND action = 'learned'""",
        (user_id, plan_id)
    )
    
    return {
        "last_node": last_session["node_name"] if last_session else None,
        "last_session": last_session["created_at"] if last_session else None,
        "learned_nodes": [r["node_id"] for r in learned],
    }
```

### Task 2: LLM Prompt 配置

**文件**: `backend/services/llm/configs/recommend_next.json`

```json
{
  "model_params": {
    "temperature": 0.5,
    "max_tokens": 1024
  },
  "system_prompt": "你是一个学习路径规划助手。基于用户的知识图谱状态、学习历史和个人背景，推荐下一步应该学习的节点。",
  "output_format": {
    "recommended_node_id": "节点ID",
    "reason": "推荐理由，用中文说明为什么推荐这个节点"
  },
  "rules": [
    "优先推荐前置依赖都已完成的节点",
    "考虑用户背景，推荐适合当前水平的节点",
    "优先推荐通往目标的关键路径上的节点",
    "如果所有节点都已完成，返回 null",
    "推荐理由要具体，提到前置完成情况或用户背景"
  ]
}
```

### Task 3: AI Service 方法

**RED**: 测试 AI recommend
```python
async def test_ai_recommend_next():
    result = await ai_service.recommend_next(
        graph={"nodes": [...], "edges": [...]},
        user_profile={"abilities": [...]},
        learning_history={"learned_nodes": [...]},
        learning_goal="..."
    )
    assert result.success
    assert "recommended_node_id" in result.data
    assert "reason" in result.data
```

**GREEN**: 实现方法
```python
# services/ai_service.py
async def recommend_next(
    self,
    graph: dict,
    user_profile: dict,
    learning_history: dict,
    learning_goal: str
) -> AIResult:
    config = load_ai_config("recommend_next")
    
    user_prompt = json.dumps({
        "graph": graph,
        "user_profile": user_profile,
        "learning_history": learning_history,
        "learning_goal": learning_goal
    }, ensure_ascii=False)
    
    result = await self.llm_client.chat_json(
        system_prompt=config["system_prompt"],
        user_prompt=user_prompt,
        **config["model_params"]
    )
    # ... 解析和验证
```

### Task 4: API 端点

**文件**: `backend/routers/ai.py`

```python
@router.post("/recommend-next")
async def recommend_next(
    request: RecommendRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """AI推荐下一学习节点"""
    # 1. 获取图谱数据
    graph = await get_graph_data(request.plan_id, db)
    # 2. 获取用户画像
    profile = await get_user_profile(current_user_id, db)
    # 3. 获取学习历史
    history = await get_learning_history(current_user_id, request.plan_id, db)
    # 4. 调用AI
    ai_service = get_ai_service()
    result = await ai_service.recommend_next(
        graph=graph,
        user_profile=profile,
        learning_history=history,
        learning_goal=graph["target_node"]["name"]
    )
    return {"success": True, "data": result.data}
```

### Task 5: 前端对接

**文件**: `frontend/src/services/api.js`

```javascript
recommendNext: async (planId) => {
  return await fetchApi(`/ai/recommend-next`, {
    method: 'POST',
    body: JSON.stringify({ planId }),
  });
},
```

**文件**: `frontend/src/hooks/useGraphInteraction.js`

```javascript
// 添加AI推荐逻辑
const recommendedNode = useMemo(() => {
  // 优先使用后端AI推荐
  if (aiRecommendation) {
    return nodes.find(n => n.id === aiRecommendation.recommended_node_id);
  }
  // 降级到规则引擎
  return nodes.find(n => 
    n.status === 'unlearned' && 
    edges.filter(e => e.to === n.id)
      .every(e => nodes.find(fn => fn.id === e.from)?.status !== 'unlearned')
  );
}, [nodes, edges, aiRecommendation]);
```

### 验收标准
- [ ] 后端 `/api/ai/recommend-next` 端点可用
- [ ] LLM 根据学习历史和用户背景生成推荐理由
- [ ] 前端优先使用后端推荐，失败时降级到规则引擎
- [ ] E2E 测试验证推荐逻辑

---

## Phase 7: AI apply-changes 后端

### 目标
实现 clarify-goal 后的真正图谱修改。

### PRD 要求（293-367行）

用户点击"应用修改"后，应该：
1. 保留现有节点及其状态
2. 新增需要的节点
3. 移除不再相关的节点
4. 保留学习进度（已学节点状态不变）

### 当前实现
```javascript
// GraphPage.jsx:119-123
const handleApplyClarify = () => {
  setShowGoalClarification(false);
  setClarifyResult(null);
  navigate(`/?goal=${encodeURIComponent(newGoalInput)}`); // ❌ 只是跳转新建
};
```

### Task 1: 数据模型

**RED**: 测试 apply-changes 数据结构
```python
def test_apply_changes_request():
    request = ApplyChangesRequest(
        plan_id="p1",
        changes={
            "keep": [{"node_id": "n1", "name": "矩阵乘法"}],
            "add": [{"temp_id": "new1", "name": "Python实现", ...}],
            "remove": [{"node_id": "n2", "name": "泰勒展开"}]
        }
    )
    assert request.plan_id
```

### Task 2: API 端点

```python
@router.post("/plans/{plan_id}/apply-changes")
async def apply_changes(
    plan_id: str,
    request: ApplyChangesRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """应用目标调整，修改现有图谱"""
    # 1. 验证 plan 所有权
    # 2. 保留节点：状态不变
    # 3. 新增节点：调用 AI 生成完整内容
    # 4. 移除节点：删除（或标记为 archived）
    # 5. 更新边关系
    # 6. 更新计划标题
```

### Task 3: 前端对接

```javascript
// api.js
applyChanges: async (planId, changes) => {
  return await fetchApi(`/plans/${planId}/apply-changes`, {
    method: 'POST',
    body: JSON.stringify({ changes }),
  });
},

// GraphPage.jsx
const handleApplyClarify = async () => {
  if (clarifyResult.isLargeChange) {
    navigate(`/?goal=${encodeURIComponent(newGoalInput)}`);
  } else {
    await planApi.applyChanges(planId, clarifyResult.changes);
    // 刷新图谱数据
    loadPlanData();
    setShowGoalClarification(false);
  }
};
```

### 验收标准
- [ ] 小幅调整时修改现有图谱，不新建
- [ ] 已学节点状态保留
- [ ] 新增节点调用 AI 生成完整内容
- [ ] E2E 测试验证修改流程

---

## Phase 8: 节点详情完善（mastery & resources）

### 目标
补齐 PRD 要求的节点卡片内容。

### PRD 要求（卡片内容顺序）
1. 标题 + 关闭按钮
2. 状态操作
3. 为什么学
4. 学什么
5. **掌握标准** ← 缺失
6. 学习Prompt
7. **推荐资源** ← 缺失
8. 我的笔记

### Task 1: 掌握标准组件

**文件**: `frontend/src/components/node/MasteryChecklist.jsx`

```jsx
export function MasteryChecklist({ items, nodeStatus }) {
  if (!items?.length) return null;
  
  return (
    <section className="space-y-3">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
        <CheckCircle size={14} /> 掌握标准
      </h4>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 text-sm">
            <input 
              type="checkbox" 
              checked={nodeStatus === 'learned'}
              readOnly
              className="mt-0.5"
            />
            <span className="text-zinc-600">{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

### Task 2: 推荐资源组件

**文件**: `frontend/src/components/node/ResourceList.jsx`

```jsx
export function ResourceList({ resources }) {
  if (!resources?.length) return null;
  
  return (
    <section className="space-y-3">
      <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2">
        <ExternalLink size={14} /> 推荐资源
      </h4>
      <div className="space-y-2">
        {resources.map((r, i) => (
          <a
            key={i}
            href={r.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 bg-zinc-50 rounded-lg hover:bg-zinc-100 transition-colors"
          >
            <div className="font-medium text-sm text-zinc-800 flex items-center gap-2">
              {r.name}
              {r.url && <ExternalLink size={12} className="text-zinc-400" />}
            </div>
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

### Task 3: "搜索更多资源"按钮

```jsx
<button
  onClick={() => window.open(
    `https://www.google.com/search?q=${encodeURIComponent(selectedNode.name + ' 学习教程')}`,
    '_blank'
  )}
  className="w-full py-2 text-sm text-zinc-500 hover:text-zinc-800 border border-dashed border-zinc-300 rounded-lg hover:border-zinc-400 transition-colors"
>
  搜索更多资源 ↗
</button>
```

### Task 4: GraphPage 集成

在节点详情面板插入（prompt 和 notes 之间）：

```jsx
{selectedNode.mastery?.length > 0 && (
  <MasteryChecklist 
    items={selectedNode.mastery} 
    nodeStatus={selectedNode.status}
  />
)}

{selectedNode.resources?.length > 0 && (
  <ResourceList resources={selectedNode.resources} />
)}

<button onClick={handleSearchMoreResources}>
  搜索更多资源 ↗
</button>
```

### 验收标准
- [ ] 节点卡片显示掌握标准（可勾选样式）
- [ ] 节点卡片显示推荐资源（带链接）
- [ ] 有"搜索更多资源"按钮，跳转 Google
- [ ] E2E 测试验证展示逻辑

---

## Phase 9: 笔记体验优化

### 目标
完善笔记功能：删除、分组、筛选、精准跳转。

### Task 1: 笔记删除功能

**RED**: 测试删除笔记
```javascript
test('can delete note', async () => {
  await page.click('[data-testid="note-menu"]');
  await page.click('[data-testid="delete-note"]');
  await page.click('[data-testid="confirm-delete"]');
  await expect(page.locator('[data-testid="note-item"]')).toHaveCount(0);
});
```

**GREEN**: 实现删除
```javascript
// api.js
deleteNote: async (noteId) => {
  return await fetchApi(`/notes/${noteId}`, { method: 'DELETE' });
},

// GraphPage.jsx - 笔记卡片添加菜单
const handleDeleteNote = async (noteId) => {
  if (!confirm('确定删除这条笔记吗？')) return;
  await notesApi.deleteNote(noteId);
  // 刷新笔记列表
  loadNotes();
};
```

### Task 2: 笔记按计划分组

**文件**: `frontend/src/pages/MyLearningPage.jsx` - Notes Tab

```jsx
// 按计划分组
const notesByPlan = useMemo(() => {
  const grouped = {};
  filteredNotes.forEach(note => {
    const planId = note.planId;
    if (!grouped[planId]) grouped[planId] = [];
    grouped[planId].push(note);
  });
  return grouped;
}, [filteredNotes]);

// 渲染
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

### Task 3: 计划筛选器

```jsx
const [selectedPlan, setSelectedPlan] = useState('all');

const filteredNotes = useMemo(() => {
  if (selectedPlan === 'all') return allNotes;
  return allNotes.filter(n => n.planId === selectedPlan);
}, [allNotes, selectedPlan]);

// UI
<select 
  value={selectedPlan}
  onChange={e => setSelectedPlan(e.target.value)}
>
  <option value="all">全部计划</option>
  {plans.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
</select>
```

### Task 4: 精准跳转

**路由**: `/graph/:planId?node=:nodeId`

```jsx
// GraphPage.jsx
import { useSearchParams } from 'react-router-dom';

const [searchParams] = useSearchParams();
const highlightNodeId = searchParams.get('node');

useEffect(() => {
  if (highlightNodeId && nodes.length > 0) {
    setSelectedNodeId(highlightNodeId);
    // 可选：自动平移视图到该节点
  }
}, [highlightNodeId, nodes]);

// NoteCard.jsx
const handleClick = () => {
  navigate(`/graph/${note.planId}?node=${note.nodeId}`);
};
```

### 验收标准
- [ ] 笔记可删除
- [ ] 笔记按计划分组显示
- [ ] 可选择计划筛选笔记
- [ ] 点击笔记跳转到具体节点并高亮
- [ ] E2E 测试通过

---

## Phase 10: 进度同步与用户画像

### Task 1: 首页进度实时同步

**方案**: Context 状态同步

```javascript
// AppContext.jsx
const updateNodeStatus = async (planId, nodeId, status) => {
  await graphApi.updateNodeStatus(planId, nodeId, status);
  
  // 更新 plans 中的进度
  setPlans(prev => prev.map(plan => {
    if (plan.id !== planId) return plan;
    
    const updatedNodes = plan.nodes.map(n => 
      n.id === nodeId ? { ...n, status } : n
    );
    const learned = updatedNodes.filter(n => n.status === 'learned').length;
    const total = updatedNodes.filter(n => n.status !== 'skipped').length;
    
    return { ...plan, progress: learned, total };
  }));
};
```

### Task 2: 编程/数学基础下拉

**文件**: `frontend/src/pages/MyLearningPage.jsx`

```jsx
<div className="space-y-2">
  <label className="text-xs font-semibold text-zinc-500">编程基础</label>
  <select
    value={userProfile?.programming_level || '入门'}
    onChange={e => actions.setUserProfile({
      ...userProfile,
      programming_level: e.target.value
    })}
    className="w-full p-3 bg-zinc-50 border border-zinc-100 rounded-lg text-sm"
  >
    {PROGRAMMING_LEVELS.map(level => (
      <option key={level} value={level}>{level}</option>
    ))}
  </select>
</div>
```

### Task 3: 已掌握知识自动汇总

**后端**: 从学习记录自动更新 `mastered_knowledge`

```python
# services/user_profile.py
async def update_mastered_knowledge(user_id: str, db):
    """从学习记录汇总已掌握知识"""
    learned_nodes = await db.fetch(
        """SELECT DISTINCT node_name 
           FROM learning_sessions 
           WHERE user_id = ? AND action = 'learned'""",
        (user_id,)
    )
    
    mastered = [r["node_name"] for r in learned_nodes]
    
    await db.execute(
        """UPDATE user_profiles 
           SET mastered_knowledge = ?, updated_at = now()
           WHERE user_id = ?""",
        (json.dumps(mastered), user_id)
    )
```

### 验收标准
- [ ] 图谱页标记已学后，首页进度即时更新
- [ ] MyLearningPage 有编程/数学基础下拉
- [ ] 已学节点自动加入"已掌握知识"
- [ ] E2E 测试通过

---

## 实施路线图

```
Phase 6: AI recommend-next (5-7天)
  ├── 学习历史聚合
  ├── LLM Prompt
  ├── AI Service
  ├── API 端点
  └── 前端对接

Phase 7: AI apply-changes (4-5天)
  ├── 数据模型
  ├── API 端点
  └── 前端对接

Phase 8: 节点详情 (2-3天)
  ├── MasteryChecklist 组件
  ├── ResourceList 组件
  ├── 搜索更多资源按钮
  └── GraphPage 集成

Phase 9: 笔记优化 (3-4天)
  ├── 删除功能
  ├── 分组展示
  ├── 计划筛选
  └── 精准跳转

Phase 10: 进度同步+画像 (2-3天)
  ├── 进度实时同步
  ├── 基础下拉字段
  └── 已掌握知识汇总
```

**总计**: 16-22 天（单人全栈）

---

## 附录：测试策略

每个 Phase 必须包含：

1. **后端单元测试**: 使用 pytest
2. **前端单元测试**: 使用 Vitest
3. **E2E 测试**: 使用 Playwright

### E2E 测试清单

- [ ] AI recommend-next 显示推荐理由
- [ ] apply-changes 保留已学状态
- [ ] 节点卡片显示掌握标准和资源
- [ ] 笔记删除后消失
- [ ] 笔记筛选器正常工作
- [ ] 点击笔记跳转到具体节点
- [ ] 首页进度自动更新

---

*文档版本: 1.0*  
*最后更新: 2026-03-17*  
*下一步: 开始 Phase 6 开发*
