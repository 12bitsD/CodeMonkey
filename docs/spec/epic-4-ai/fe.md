# Epic 4: 前端需求

## 首页: 目标解析

### 解析流程

```
1. 用户输入学习目标
2. 点击"解析"
3. 显示 Loading
4. 返回解析结果
   - interpretation: AI 的理解
   - backgroundSummary: 背景摘要
   - shouldSplit: 是否需要拆分
   - splitSuggestions: 拆分建议 (如 shouldSplit=true)
5. 用户确认或修改输入
```

### US-4.1 解析目标 UI

```
GoalInputSection
├── Textarea (placeholder: "我想学深度学习")
├── BackgroundSection (可选展开)
│   ├── ProgrammingLevel: [入门 ▼]
│   └── MathLevel: [入门 ▼]
├── ParseButton
└── ResultSection (解析后显示)
    ├── InterpretationCard
    │   └── "你，想学习深度学习..."
    ├── BackgroundSummaryList
    │   └── "✅ 有 Python 基础"
    └── SplitSuggestions (shouldSplit=true 时)
        ├── "深度学习 → 计算机视觉"
        └── "深度学习 → 自然语言处理"
```

---

## 首页: 图谱生成

### US-4.2 生成图谱

```
GraphPreviewModal
├── TitleInput
├── NodeCountSelect (可选)
├── GenerateButton
└── PreviewCanvas
    └── NodeCard (显示节点预览)
```

---

## 图谱页: 目标调整

### US-4.3 澄清目标

```
ClarifyModal
├── OriginalGoalDisplay
├── NewGoalInput
├── SubmitButton
└── ChangesPreview (显示 AI 返回的变更)
    ├── Keep: [节点列表]
    ├── Remove: [节点列表] (红色)
    └── Add: [节点列表] (绿色)
```

---

## 图谱页: AI 推荐

### US-4.4 AI 推荐下一节点

- 节点详情面板中显示 AI 推荐
- 推荐节点有特殊高亮/边框
- 显示推荐原因

```
NodeDetailPanel
├── AIRecommendation
│   ├── "推荐学习: Python基础"
│   └── "原因: 你有Java基础，可快速上手"
```

---

## API 调用

```javascript
// 解析目标
aiApi.parseGoal(input, userProfile)

// 生成图谱
aiApi.generateGraph(input, interpretation, userProfile)

// 澄清目标
aiApi.clarifyGoal(originalGoal, newGoal, planId)

// 推荐下一节点
aiApi.recommendNext(planId)

// 应用变更
graphApi.applyChanges(planId, { keep, remove, add, newTitle })
```
