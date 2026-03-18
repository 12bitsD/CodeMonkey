# 前端 - 我的学习页 (MyLearningPage)

**路由**: `/my-learning`  
**文件**: `src/pages/MyLearningPage.jsx`

一致性标记：❌（plans 归档/恢复/删除仍为 Mock；stats 未对接后端）

---

## 功能概述

"我的学习"页面包含4个Tab：

1. **我的画像** - 查看/编辑个人背景信息
2. **归档计划** - 管理已归档的学习计划
3. **全部笔记** - 浏览所有笔记，支持搜索
4. **学习统计** - 查看学习数据统计

---

## 页面结构

```
┌─────────────────────────────────────────────────────┐
│ [←] 我的学习                                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │ [我的画像]   │  │                             │ │
│  │  归档计划    │  │    Tab 内容区               │ │
│  │  全部笔记    │  │                             │ │
│  │  学习统计    │  │                             │ │
│  └──────────────┘  └─────────────────────────────┘ │
│       侧边导航              主内容区                │
└─────────────────────────────────────────────────────┘
```

---

## 组件状态

```javascript
const [activeTab, setActiveTab] = useState("profile");
const [searchQuery, setSearchQuery] = useState(""); // 笔记搜索

// 从 Context 获取
const { userProfile, plans, allNotes, actions } = useAppContext();

// 计算数据
const archivedPlans = plans.filter((p) => p.status === "archived");
const activePlans = plans.filter((p) => p.status === "active");
const filteredNotes = searchQuery
  ? allNotes.filter((n) => n.content.includes(searchQuery))
  : allNotes;
```

---

## Tab: 我的画像

### 功能

- 编辑基础信息（职业、教育背景）
- 管理能力标签（添加/删除）
- 查看已掌握知识（只读）

### UI组件

**基础信息**

```jsx
<input
  value={userProfile?.occupation || ''}
  onChange={e => actions.setUserProfile({...userProfile, occupation: e.target.value})}
/>
<input
  value={userProfile?.education || ''}
  onChange={e => actions.setUserProfile({...userProfile, education: e.target.value})}
/>
```

**能力标签**

```jsx
{
  userProfile?.abilities?.map((tag, i) => (
    <Badge key={i} onDelete={() => handleRemoveAbility(i)}>
      {tag}
    </Badge>
  ));
}
<button onClick={handleAddAbility}>+ 添加</button>;
```

**已掌握知识**

- 来源：`userProfile.masteredKnowledge`
- 只读显示，由学习完成后系统自动添加

### 操作函数

```javascript
const handleAddAbility = () => {
  const newAbility = prompt("添加新的能力标签:");
  if (newAbility?.trim()) {
    actions.setUserProfile({
      ...userProfile,
      abilities: [...(userProfile.abilities || []), newAbility.trim()],
    });
  }
};

const handleRemoveAbility = (index) => {
  const newAbilities = [...userProfile.abilities];
  newAbilities.splice(index, 1);
  actions.setUserProfile({ ...userProfile, abilities: newAbilities });
};
```

---

## Tab: 归档计划

### 功能

- 显示已归档的计划列表
- 恢复计划到首页
- 删除计划（未实现）

### UI组件

```jsx
{
  archivedPlans.map((plan) => (
    <div className="plan-card">
      <h3>{plan.title}</h3>
      <p>最后访问: {plan.lastAccess}</p>
      {plan.progress === plan.total && <span>已完成</span>}
      <Button onClick={() => handleRestore(plan.id)}>恢复</Button>
    </div>
  ));
}
```

### 操作函数

```javascript
const handleRestore = async (id) => {
  await actions.updatePlan(id, { status: "active" });
};
```

### 空状态

```jsx
<div className="empty-state">
  <Archive size={48} />
  暂无归档计划
</div>
```

---

## Tab: 全部笔记

### 功能

- 按时间倒序显示所有笔记
- 支持关键词搜索
- 点击笔记跳转对应图谱

### UI组件

**搜索框**

```jsx
<input
  placeholder="搜索笔记..."
  value={searchQuery}
  onChange={(e) => setSearchQuery(e.target.value)}
/>
```

**笔记卡片**

```jsx
{
  filteredNotes.map((note) => (
    <div
      onClick={() => navigate(`/graph/${note.planId}`)}
      className="note-card"
    >
      <span className="date">{note.date}</span>
      <p className="content">{note.content}</p>
    </div>
  ));
}
```

### 空状态

```jsx
{
  searchQuery ? "没有找到匹配的笔记" : "暂无笔记";
}
```

---

## Tab: 学习统计

### 功能

- 显示总览数据（4个统计卡片）
- 显示知识领域分布图（柱状图）

### 统计数据

```javascript
const completedPlansCount = archivedPlans.filter(
  (p) => p.progress === p.total && p.total > 0,
).length;

const masteredKnowledgeCount = userProfile?.masteredKnowledge?.length || 0;
```

### UI组件

**总览**

```jsx
<div className="stats-grid">
  <StatCard label="已完成计划" value={completedPlansCount} />
  <StatCard label="进行中" value={activePlans.length} />
  <StatCard label="掌握知识点" value={masteredKnowledgeCount} />
  <StatCard label="学习笔记" value={allNotes.length} />
</div>
```

**知识领域分布**

```jsx
{
  masteredKnowledgeCount > 0 ? (
    <>
      <ChartBar label="深度学习" value={0} color="bg-teal-500" count={0} />
      <ChartBar label="数学基础" value={0} color="bg-blue-500" count={0} />
      <ChartBar label="编程" value={0} color="bg-amber-500" count={0} />
    </>
  ) : (
    <div>开始学习后，这里将显示你的知识领域分布</div>
  );
}
```

**注意**：当前领域分布是写死的，需要对接后端 `/api/stats/distribution` 接口。

---

## API调用

### 当前实现

数据主要来自 `AppContext`：

- userProfile：登录后通过后端 `/api/user/profile` 加载，更新也走后端
- plans：登录后通过后端 `/api/plans` 加载，但归档/恢复/删除当前仍为 Mock
- notes：本地 Mock（LocalStorage）
- stats：当前未对接后端，页面内有占位/写死分布

### 待对接接口

| 功能     | 接口                              |
| -------- | --------------------------------- |
| 恢复计划 | `PUT /api/plans/{planId}/restore` |
| 删除计划 | `DELETE /api/plans/{planId}`      |
| 获取统计 | `GET /api/stats/overview`         |
| 知识分布 | `GET /api/stats/distribution`     |

---

## 待实现功能

| 功能              | 说明                           |
| ----------------- | ------------------------------ |
| 删除计划          | 归档Tab添加删除按钮            |
| 编程/数学基础选择 | 画像Tab添加下拉选择            |
| 笔记按计划分组    | 当前是平铺显示                 |
| 笔记编辑/删除     | 当前只能查看                   |
| 真实统计数据      | 对接后端统计接口               |
| 本周学习数据      | 展示本周完成节点数、新增笔记数 |
