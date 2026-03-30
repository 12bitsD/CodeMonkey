# Epic 2: 前端需求

## 页面: 首页 (`/`)

### 功能

**US-2.1 创建计划 (AI 生成)**
- 输入学习目标
- 可选: 输入背景 (编程/数学水平)
- 解析目标 (parse-goal)
- 确认生成
- 创建计划

**US-2.2 查看计划列表**
- 显示进行中的计划 (active)
- 显示进度条
- 显示最近活动时间

### 交互流程

```
1. 用户输入: "我想学深度学习"
2. 前端调用 aiApi.parseGoal()
3. 显示解析结果 (interpretation, backgroundSummary)
4. 用户确认
5. 前端调用 graphApi.generate() 或 aiApi.generateGraph()
6. 显示图谱预览
7. 用户确认
8. 前端调用 plansApi.create()
9. 跳转到 /graph/{planId}
```

### 组件

```
HomePage
├── HeroSection
│   ├── GoalInput (textarea)
│   ├── BackgroundSelector (可选)
│   └── GenerateButton
├── GoalConfirmModal (clarify 后显示)
│   ├── InterpretationView
│   └── ConfirmButton
├── PlanList
│   └── PlanCard (循环)
│       ├── Title
│       ├── ProgressBar
│       ├── ProgressText ("3/10 已学习")
│       └── LastAccess
└── Toast (错误提示)
```

---

## 页面: 图谱页 (`/graph/:planId`)

### 功能

**US-2.3 查看图谱**
- 画布显示节点和边
- 节点可拖拽
- 点击节点显示详情

**US-2.4 更新节点状态**
- 双击切换状态
- 或右键菜单选择

**US-2.5/2.6 节点位置**
- 拖拽调整位置
- 自动保存或手动保存

### 画布交互

| 操作 | 行为 |
|------|------|
| 拖拽节点 | 更新节点 x, y |
| 双击节点 | 切换 unlearned ↔ learned |
| 右键节点 | 显示菜单 (标记已学/跳过/查看详情) |
| 滚轮 | 缩放 |
| 拖拽空白处 | 平移画布 |
| 点击边 | 高亮依赖路径 |

### 组件

```
GraphPage
├── Canvas
│   ├── SVG (边)
│   │   └── EdgeLine (循环)
│   │       └── ArrowMarker
│   └── Nodes (循环)
│       └── NodeCard
│           ├── Title
│           ├── StatusBadge
│           └── TargetIcon (isTarget 时显示)
├── NodeDetailPanel (选中节点时显示)
│   ├── NodeHeader
│   │   ├── Name
│   │   └── StatusBadge
│   ├── WhySection
│   ├── WhatSection
│   ├── MasteryChecklist
│   ├── ResourceList
│   └── NotesButton
├── Toolbar
│   ├── ZoomIn
│   ├── ZoomOut
│   ├── ResetView
│   └── SaveButton
├── LeaveConfirmModal (有未保存更改时)
└── CompleteCelebration (所有节点完成时)
```

---

## 节点状态 UI

| Status | 颜色 | 图标 |
|--------|------|------|
| unlearned | 灰色 | Circle |
| learned | 绿色 | CheckCircle2 |
| skipped | 橙色 | XCircle |

---

## 组件状态

### NodeCard

```typescript
interface NodeCardProps {
  node: Node;
  isSelected: boolean;
  isRecommended: boolean;  // AI 推荐
  onSelect: () => void;
  onStatusChange: (status) => void;
  onPositionChange: (x, y) => void;
}
```

### useGraphInteraction Hook

```typescript
const {
  nodes,
  edges,
  selectedNodeId,
  scale,
  position,
  setSelectedNodeId,
  setDraggingNodeId,
  handleWheel,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  setNodeStatus,
  setNodes,
  setEdges,
} = useGraphInteraction(initialNodes, initialEdges, aiRecommendation)
```

---

## API 调用

```javascript
// 生成图谱
graphApi.generate(input, interpretation, userBackground)

// 获取图谱
graphApi.get(planId)

// 更新节点状态
graphApi.updateNodeStatus(planId, nodeId, status)

// 保存节点位置
graphApi.updateNodePosition(planId, nodeId, x, y)

// 批量保存位置
graphApi.updateNodePositions(planId, positions)

// 创建计划
plansApi.create({ title, originalInput, targetNodeId, nodes, edges })
```
