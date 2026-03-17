# 前端 - 首页 (HomePage)

**路由**: `/`  
**文件**: `src/pages/HomePage.jsx`

一致性标记：✅（AI/生成/创建计划均已接入真实后端；拆分建议 UI 已实现；Toast 错误提示缺失）

---

## 功能概述

首页是用户的主入口，包含两个核心功能：

1. **输入学习目标** → 生成知识图谱
2. **继续学习** → 查看进行中的计划

---

## 页面结构

```
┌─────────────────────────────────────────┐
│ [Logo]                    [登录/注册]   │  ← Header
├─────────────────────────────────────────┤
│                                         │
│       今天想掌握什么？                   │  ← 标题
│                                         │
│  ┌─────────────────────────────────────┐│
│  │ 输入学习目标...                     ││  ← 输入区
│  │                                     ││
│  │ [能力标签]        [生成图谱]        ││
│  └─────────────────────────────────────┘│
│                                         │
│  [示例按钮] [示例按钮] [示例按钮]       │  ← 示例（输入为空时）
│                                         │
├─────────────────────────────────────────┤
│  继续学习                               │
│  ┌──────────────┐ ┌──────────────┐     │  ← 计划卡片
│  │ 计划1    ⋮  │ │ 计划2    ⋮  │     │
│  │ ████░░ 60%  │ │ ░░░░░░ 0%   │     │
│  └──────────────┘ └──────────────┘     │
└─────────────────────────────────────────┘
```

---

## 组件状态

```javascript
// 输入相关
const [inputText, setInputText] = useState("");
const [isAnalyzing, setIsAnalyzing] = useState(false); // 解析中
const [isGenerating, setIsGenerating] = useState(false); // 生成中
const [loadingStep, setLoadingStep] = useState(0); // 加载动画步骤

// 弹窗相关
const [showConfirmModal, setShowConfirmModal] = useState(false);
const [parsedGoal, setParsedGoal] = useState(null);

// 计划菜单
const [activeMenuPlanId, setActiveMenuPlanId] = useState(null);
const [showRenameModal, setShowRenameModal] = useState(false);
const [planToRename, setPlanToRename] = useState(null);
const [newName, setNewName] = useState("");

// 认证（Mock）
// 当前实现使用 AuthContext + /auth 页面；首页不再承担登录弹窗的主流程
```

---

## 用户交互流程

### 1. 生成图谱流程

```
用户输入目标
    ↓
点击"生成图谱"按钮
    ↓
[isAnalyzing = true] 调用 aiApi.parseGoal()
    ↓
返回 parsedGoal: { interpretation, backgroundSummary, shouldSplit, ... }
    ↓
[showConfirmModal = true] 显示确认弹窗
    ↓
用户点击"确认生成"
    ↓
[isGenerating = true] 显示加载动画
    ↓
调用 graphApi.generate() → 获取图谱数据
    ↓
调用 actions.createPlan() → 创建计划
    ↓
navigate(`/graph/${newPlan.id}`) → 跳转图谱页
```

**实现现状**：

- `plansApi.create()` 已对接真实后端，返回真实 `planId`。
- GraphPage 进入后调用 `GET /api/plans/{planId}/graph` 拉取真实图谱数据，首页→图谱链路已闭合。

### 2. 计划操作

| 操作     | 触发        | 效果                      |
| -------- | ----------- | ------------------------- |
| 进入图谱 | 点击卡片    | `navigate(/graph/${id})`  |
| 重命名   | 菜单→重命名 | 打开重命名弹窗            |
| 归档     | 菜单→归档   | `actions.archivePlan(id)` |

---

## API调用

### parseGoal 请求/响应

```javascript
// 调用（真实后端 POST /api/ai/parse-goal）
const result = await aiApi.parseGoal(inputText, userProfile);

// 响应
{
  interpretation: "理解反向传播的数学原理",
  backgroundSummary: [
    { text: "Python入门", source: "profile", isStrength: true },
    { text: "数学薄弱", source: "input", isStrength: false }
  ],
  suggestedNodeCount: 7,
  shouldSplit: false,
  splitSuggestions: null
}
```

### generate 请求/响应

```javascript
// 调用（真实后端 POST /api/ai/generate-graph；userProfile 暂未序列化进请求体，Phase 5 补全）
const graphResult = await graphApi.generate(inputText, userProfile);

// 响应
{
  interpretation: "...",
  nodes: [{ id, name, status, x, y, why, what, mastery, prompt, ... }],
  edges: [{ from, to }], // 前端画布当前使用 from/to；后端返回为 from_node/to_node（需做字段映射）
  targetNodeId: "n1"
}
```

---

## UI组件

### Header

- **未登录**: 显示“登录/注册”，点击跳转 `/auth`
- **已登录**: 显示“我的学习”，点击跳转 `/my-learning`

### 输入区

- 多行textarea，placeholder显示示例
- 底部左侧：用户能力标签（最多2个，来自 `userProfile.abilities`）
- 底部右侧：生成按钮

### 加载动画

当 `isGenerating=true` 时，覆盖在输入区上方：

```javascript
const LOADING_TEXTS = [
  "正在理解你的学习目标...",
  "正在拆解核心知识点...",
  "正在分析依赖关系...",
  "正在搜索优质资源...",
  "正在生成学习图谱...",
];
```

### 示例按钮

当输入框为空时显示，点击自动填入：

- "理解反向传播算法"
- "Python 数据分析入门"
- "Transformer 架构详解"

### 计划卡片

- 标题 + 上次访问时间
- 进度条（`progress / total * 100%`）
- 菜单按钮（⋮）→ 重命名、归档

---

## 弹窗

### 确认学习目标弹窗

显示 `parsedGoal` 的解析结果：

- 识别目标：`interpretation`
- 基于你的背景：`backgroundSummary`（区分优势✓/弱项○）

### 重命名弹窗

- 输入框，预填当前标题
- 保存调用 `actions.updatePlan(id, { title })`

### 登录/注册弹窗

- 当前主流程为 `/auth` 页面（AuthContext）；HomePage 内部仍保留部分弹窗状态属于遗留代码，建议后续清理或复用到 `/auth`。

---

## 待实现功能

| 功能 | 状态 | 说明 |
| ---- | ---- | ---- |
| 拆分建议弹窗 | ✅ | parse-goal 返回 `shouldSplit=true` 时显示子目标卡片，可点击替换输入 |
| 真实认证 | ✅ | `/auth` + AuthContext + tokenManager |
| 全局 Toast 错误提示 | ❌ | 解析/生成失败时无可见提示；Phase 5 计划实现 |
| userBackground 传参 | ❌ | `graphApi.generate` 已接受 userProfile 参数但未序列化；Phase 5 补全 |
