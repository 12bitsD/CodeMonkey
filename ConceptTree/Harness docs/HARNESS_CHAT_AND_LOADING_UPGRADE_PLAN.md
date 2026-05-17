# ConceptTree - Harness Engineering 升级方案
> 主题：AI 助手 Markdown 渲染 + 两阶段加载动画升级
> 生成日期：2026-04-17

---

## 目标

本次升级聚焦三件事：

1. AI 学习助手聊天内容支持 Markdown 渲染，提升可读性和信息层级。
2. 用户输入学习目标并点击“生成图谱”后，在等待“澄清页面”出现前，加入更明确、更有氛围的加载动画。
3. 用户确认澄清目标后，正式生成图谱时，替换现有简陋加载 UI，升级成更完整的生成中体验。

---

## Harness 核心原则

```
Harness = 单一状态源
        + 分阶段可感知反馈
        + 视觉与语义一致
        + 回归测试守门
```

本次升级的核心要求：

1. 不新增零散 loading 状态，复用现有 `isAnalyzing / isGenerating / loadingStep / streamProgress`。
2. 不让聊天区单独写一套 Markdown 解析逻辑，统一复用已有 `MarkdownContent`。
3. 两个加载阶段必须视觉明显不同，避免用户分不清“正在理解需求”和“正在生成图谱”。
4. 升级后补测试，保证按钮流程和关键文案不回退。

---

## 现状判断

### AI 助手聊天区

当前在 `frontend/src/pages/GraphPage.jsx` 中：

- 用户消息和 AI 消息都直接按纯文本展示
- AI 回复即使包含标题、列表、代码块，也不会被格式化
- 这和核心内容解释区已经支持 Markdown 的体验不一致

### 加载阶段 1：输入目标 -> 等待澄清页面

当前在 `frontend/src/pages/HomePage.jsx` 中：

- 点击“生成图谱”先走 `handleStartAnalysis`
- 状态只有 `isAnalyzing`
- 按钮文案会变成“解析中...”
- 但页面没有真正的阶段性过渡体验

问题：

- 用户会感觉“点击后页面没有明确进入一个分析过程”
- 等待时间一长，会误以为卡住

### 加载阶段 2：确认需求 -> 正式生成图谱

当前在 `frontend/src/pages/HomePage.jsx` 中：

- `isGenerating` 时显示一个简单旋转圆圈和一行文案
- 有 `loadingStep` 和 `streamProgress`
- 但视觉信息过于单薄，缺乏“AI 正在逐步构建知识图谱”的感知

问题：

- 动画过于简陋
- 没有图谱生成的语义表达
- 与产品整体视觉语言不够统一

---

## 功能拆分

### Feature A - AI 学习助手 Markdown 渲染

目标：

- 让 AI 回复支持标题、列表、强调、引用、代码块、链接
- 保持用户消息仍是普通气泡样式
- AI 消息气泡升级为更适合长文本阅读的内容容器

建议落点：

- `frontend/src/pages/GraphPage.jsx`
- 复用 `frontend/src/components/common/MarkdownContent.jsx`

实现策略：

1. 仅 AI assistant 消息走 Markdown 渲染。
2. user 消息继续用纯文本气泡。
3. AI 消息容器增大行高、优化 padding、弱化边框、增强段落节奏。

---

### Feature B - 阶段 1 分析目标加载动画

场景：

- 用户输入概念
- 点击“生成图谱”
- 系统调用 `aiApi.parseGoal(...)`
- 在澄清页面弹出前，需要一个短暂但明确的分析中界面

目标：

- 用户立刻感知“AI 正在理解你的目标”
- 提升等待过程的可信度
- 为澄清弹窗建立更平滑的过渡

建议方案：

新增一个轻量全屏或卡片内 Overlay：

- 标题：`AI 正在理解你的学习目标`
- 副文案：动态切换，比如
  - `解析概念边界`
  - `识别你的背景与目标`
  - `生成更清晰的学习表述`
- 动画元素：
  - 中心脉冲球 + 环形扩散
  - 背景细点/轨迹线轻微漂浮
  - 3 条 staggered 文本骨架条

视觉建议：

- 保持白底，但加入淡青色和石墨灰渐层
- 用柔和发光替代普通 spinner
- 与首页 Hero 输入框视觉语言保持一致

状态建议：

- 新增 `analysisLoadingScene` 组件
- 仍由 `isAnalyzing` 控制显示

---

### Feature C - 阶段 2 正式生成图谱加载动画

场景：

- 用户确认澄清目标
- 系统开始走 `graphApi.generate(...)`
- SSE 流式返回节点进度

目标：

- 让用户看到“图谱正在被构建”
- 放大 `streamProgress` 的价值
- 明确当前处于生成阶段，而非目标分析阶段

建议方案：

将当前简易 spinner 升级为“图谱生成仪表面板”：

- 主标题：`正在为你生成学习图谱`
- 副标题：`从目标拆解到知识节点排序，AI 正在逐步构建`
- 中央动画：
  - 3-5 个发光节点
  - 节点之间连线逐步点亮
  - 节点轻微漂浮，模拟图谱生长
- 进度呈现：
  - 如果有 `streamProgress`，显示 `已生成 X / Y 个节点`
  - 如果没有，就显示语义阶段文案
- 底部信息条：
  - `构建核心概念`
  - `排序前置依赖`
  - `组织学习路径`

视觉建议：

- 比阶段 1 更具结构感
- 使用线条、节点、网络关系作为视觉核心
- 弱化传统 spinner

---

## 推荐组件拆分

### 1. ChatMarkdownMessage

建议新增：

- `frontend/src/components/chat/ChatMarkdownMessage.jsx`

职责：

- 只负责 AI 消息内容展示
- 内部直接使用 `MarkdownContent`
- 封装 AI 消息气泡样式

### 2. GoalAnalysisLoader

建议新增：

- `frontend/src/components/loaders/GoalAnalysisLoader.jsx`

职责：

- 首页输入目标后、澄清弹窗前的加载展示
- 控制动态文案和过渡动画

### 3. GraphGenerationLoader

建议新增：

- `frontend/src/components/loaders/GraphGenerationLoader.jsx`

职责：

- 正式生成图谱阶段展示
- 接收 `loadingStep` 和 `streamProgress`
- 呈现图谱生成感的视觉动画

---

## 状态设计建议

### 首页

当前已有：

- `isAnalyzing`
- `isGenerating`
- `loadingStep`
- `streamProgress`

建议保持不变，只优化映射方式：

- `isAnalyzing` -> 显示 `GoalAnalysisLoader`
- `isGenerating` -> 显示 `GraphGenerationLoader`

不要新增过多布尔值，避免状态交叉污染。

### 图谱页聊天区

当前已有：

- `chatMessages`
- `chatLoading`

建议不新增消息渲染状态，只在 UI 分支中根据 `msg.role` 区分：

- `user` -> 普通气泡
- `assistant` -> Markdown 卡片气泡

---

## 视觉语言建议

### 阶段 1：理解目标

关键词：

- 轻
- 柔和
- 理解中
- 尚未成型

设计特征：

- 呼吸感
- 扩散感
- 模糊边缘
- 文本骨架

### 阶段 2：生成图谱

关键词：

- 结构化
- 构建中
- 网络感
- 成长感

设计特征：

- 节点连线
- 进度点亮
- 层级递进
- 更明确的信息面板

---

## 风险与守门

### 风险 1 - 动画太重影响性能

问题：

- 首页和图谱页都已经有不少动效
- 如果再加大面积 blur / box-shadow / 无限动画，可能影响中低端设备

守门策略：

- 优先 CSS transform / opacity 动画
- 避免大面积频繁 box-shadow repaint
- 节点数量控制在 3-5 个

### 风险 2 - Markdown 渲染导致聊天气泡高度失控

问题：

- AI 回复若带多级列表或长代码块，聊天区可能溢出

守门策略：

- 给代码块加 `overflow-x-auto`
- 限制 AI 气泡最大宽度
- 保持聊天区滚动逻辑稳定

### 风险 3 - 两阶段视觉太相似

问题：

- 用户分不清“正在理解目标”和“正在生成图谱”

守门策略：

- 标题文案必须不同
- 动画语义必须不同
- 阶段 1 偏抽象感，阶段 2 偏结构感

---

## Harness Hooks / 自动检查建议

### Hook A - 聊天渲染改动后跑 Markdown 测试

触发条件：

- 编辑 `GraphPage.jsx`
- 编辑 `ChatMarkdownMessage.jsx`
- 编辑 `MarkdownContent.jsx`

执行：

```bash
cd frontend && npx vitest run src/components/common/MarkdownContent.test.jsx --pool=threads
```

### Hook B - 首页加载动画改动后跑页面测试

触发条件：

- 编辑 `HomePage.jsx`
- 编辑 `GoalAnalysisLoader.jsx`
- 编辑 `GraphGenerationLoader.jsx`

执行：

```bash
cd frontend && npx vitest run src/pages/HomePage.test.jsx --pool=threads
```

### Hook C - 前端动效改动后跑精确 lint

执行：

```bash
cd frontend && npx eslint src/pages/HomePage.jsx src/pages/GraphPage.jsx src/components/loaders src/components/chat
```

---

## 测试计划

### 前端单元测试

建议新增：

| 测试文件 | 覆盖点 |
|------|------|
| `frontend/src/components/chat/ChatMarkdownMessage.test.jsx` | AI 回复 Markdown 是否正确渲染 |
| `frontend/src/pages/HomePage.loading.test.jsx` | `isAnalyzing` 时展示目标分析动画 |
| `frontend/src/pages/HomePage.loading.test.jsx` | `isGenerating` 时展示图谱生成动画 |
| `frontend/src/pages/HomePage.loading.test.jsx` | `streamProgress` 文案是否正确更新 |

### 手动验证清单

1. 在首页输入一个概念并点击“生成图谱”。
2. 确认立刻出现“理解目标”的加载界面，而不是只有按钮变文案。
3. 确认几秒后进入澄清弹窗。
4. 确认澄清后进入“生成图谱”动画界面。
5. 检查进度文案随 SSE 节点返回变化。
6. 进入图谱页聊天助手，让 AI 输出列表、标题、代码块。
7. 确认 AI 回复在聊天区内以 Markdown 形式显示。

### 测试脚本建议

建议新增：

```powershell
scripts/test_chat_and_loading_upgrade.ps1
```

脚本执行建议：

```powershell
cd frontend
npx vitest run src/components/common/MarkdownContent.test.jsx --pool=threads
npx vitest run src/pages/HomePage.test.jsx --pool=threads
npx eslint src/pages/HomePage.jsx src/pages/GraphPage.jsx src/components/loaders src/components/chat
```

---

## 推荐实施顺序

1. 先做聊天区 AI 回复 Markdown 渲染。
2. 抽出 `GoalAnalysisLoader`，接到 `isAnalyzing`。
3. 抽出 `GraphGenerationLoader`，替换当前 `isGenerating` 覆盖层。
4. 调整首页测试和 lint。
5. 整理脚本并回归验证。

---

## 本次结论

这三项升级适合打包成一次前端体验强化 Sprint：

- 聊天区 Markdown 渲染解决信息表达问题
- 阶段 1 动画解决“点击后等待澄清”的空窗感
- 阶段 2 动画解决“正式生成图谱”阶段过于简陋的问题

按 Harness Engineering 的方式推进，重点不是只把动画做出来，而是：

- 明确阶段
- 统一状态
- 复用已有渲染能力
- 用测试和脚本守住回归
