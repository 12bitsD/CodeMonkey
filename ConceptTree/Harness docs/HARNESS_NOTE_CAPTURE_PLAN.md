# ConceptTree - Harness Engineering 更新计划
> 主题：AI 学习助手内容沉淀到笔记 + 核心内容一键保存到笔记
> 生成日期：2026-04-17

---

## 目标

在不增加认知负担的前提下，把用户在图谱页里已经产生的高价值内容更顺滑地沉淀到笔记系统：

1. AI 学习助手支持将一段对话内容总结后保存到笔记。
2. 核心内容区的 AI 解释支持一键保存到笔记。

最终效果：

- 用户不用复制粘贴，就能把 AI 产出的有效内容沉淀到个人知识库。
- 笔记入口统一走现有 `notes` 数据流，避免生成第二套“临时收藏”状态。
- 所有保存动作都可测试、可追踪、可恢复。

---

## Harness 核心原则

```
Harness = 明确入口
        + 单一保存通道
        + 守门校验
        + 自动测试
        + 失败可恢复
```

这次更新的 Harness 关注点：

1. 不允许前端到处散落临时保存逻辑，统一复用 `NoteContext.actions.addNote`。
2. 所有 AI 到笔记的落地内容都先经过前端 summary/format 规则，保证可读性和长度可控。
3. 对新增按钮、保存成功、保存失败、去重提示建立测试闭环。

---

## 功能拆分

### Feature A - AI 学习助手对话总结后保存到笔记

用户路径：

1. 在右下角 AI 学习助手中完成若干轮对话。
2. 点击“总结并保存到笔记”按钮。
3. 前端提取当前对话上下文，生成一份适合笔记展示的摘要文本。
4. 调用现有 `noteActions.addNote(planId, selectedNodeId, summary)` 保存。
5. 保存成功后给出 toast，并让用户能在当前节点笔记区和“我的学习 -> 笔记”里看到内容。

### Feature B - 核心内容解释一键保存到笔记

用户路径：

1. 用户点击核心内容主题，展开 AI 解释。
2. 在已展开的解释卡片上点击“保存到笔记”。
3. 前端将“主题标题 + AI 解释正文”格式化为一条结构化笔记。
4. 调用同一个 `noteActions.addNote(...)` 保存。
5. 保存成功后即时提示，并避免重复狂点导致连续插入重复内容。

---

## 现状判断

基于当前代码结构，功能可以在现有架构内落地：

- 聊天消息状态已存在于 `frontend/src/pages/GraphPage.jsx`
- 核心内容解释状态已存在于 `explainStates`
- 笔记统一入口已存在于 `frontend/src/contexts/NoteContext.jsx`
- 笔记后端 API 已存在于 `frontend/src/services/api.js` 的 `notesApi.create`

结论：

- 不需要新增后端表
- 不需要新增单独的 summary 存储模型
- 第一版可以只做前端格式化总结 + 调用已有 notes API
- 如果后续觉得摘要质量不够，再追加后端 `/ai/summarize-note` 能力作为 Sprint 2

---

## Sprint 1 - 最小可用版本

### 代码任务

| 任务 | 文件 | 说明 |
|------|------|------|
| 为聊天面板增加“总结并保存到笔记”按钮 | `frontend/src/pages/GraphPage.jsx` | 按钮仅在有聊天内容时可用 |
| 新增聊天内容转笔记摘要函数 | `frontend/src/pages/GraphPage.jsx` 或 `frontend/src/utils/` | 将聊天消息整理为短摘要 |
| 为核心内容解释卡片增加“保存到笔记”按钮 | `frontend/src/pages/GraphPage.jsx` | 仅在 `state.content` 存在时显示 |
| 提取统一的笔记内容格式化函数 | `frontend/src/utils/` | 避免聊天保存和解释保存各写一套 |
| 增加保存中的 loading / 防重复点击状态 | `frontend/src/pages/GraphPage.jsx` | 按钮点击后禁用，防止重复提交 |
| 保存成功后 toast + 可选高亮最新笔记 | `frontend/src/pages/GraphPage.jsx` | 强化反馈闭环 |

### 建议新增工具函数

建议新增：

- `buildChatSummaryNote(messages, nodeName)`
- `buildExplainNote(topicTitle, content, nodeName)`
- `dedupeNoteCandidate(existingNotes, nextContent)`

职责要求：

- 统一标题格式
- 截断无意义冗长内容
- 清理重复空行
- 对 Markdown 保持原样，不破坏层级

---

## Sprint 2 - 体验增强

### AI 助手总结质量升级

如果 Sprint 1 的前端摘要不足够自然，再追加：

| 任务 | 文件 | 说明 |
|------|------|------|
| 新增 AI 总结接口 | `backend/routers/ai.py` | 输入聊天记录，输出适合保存的摘要 |
| Prompt 增加“输出适合笔记保存的 Markdown”约束 | `backend/services/` | 固定结构，减少噪音 |
| 前端保存前优先调用 summary API | `frontend/src/services/api.js` | 失败时回退到本地摘要 |

### UX 细化

- 聊天助手里增加“保存原文”和“保存总结”二选一
- 核心内容卡片保存后显示“已保存”短状态
- 对相同内容二次保存给出“已存在相似笔记”的轻提示

---

## 笔记格式规范

### 聊天总结笔记格式

建议第一版保存为：

```md
## AI 学习助手总结

知识点：{nodeName}

### 结论
{summary}

### 来自对话
- 用户关注：...
- AI 说明：...
```

要求：

- 优先保留结论、易错点、建议动作
- 不原样塞入整段长对话
- 保持在适合卡片预览的长度

### 核心内容解释笔记格式

建议第一版保存为：

```md
## 核心内容笔记

知识点：{nodeName}
主题：{topicTitle}

{content}
```

要求：

- 保留现有 Markdown 渲染内容
- 标题和来源信息清晰
- 让“我的学习”页能直接读懂这条笔记来自哪里

---

## 状态与交互设计

### 聊天总结保存

- 条件：`chatMessages.length > 0`
- 按钮文案：
  - 默认：`总结并保存`
  - 保存中：`保存中...`
  - 成功短态：`已保存`
- 异常提示：
  - 无节点上下文：`请先选择一个知识点`
  - 对话为空：`暂无可总结内容`
  - 保存失败：`保存失败，请重试`

### 核心内容保存

- 条件：`state.content && !state.loading`
- 按钮位置：解释卡片右上或底部操作条
- 按钮文案：
  - 默认：`保存到笔记`
  - 保存中：`保存中...`
  - 成功短态：`已保存`

---

## 风险与守门

### 风险 1 - 重复保存

问题：

- 用户连续点击
- 同一解释内容被多次落库

守门策略：

- 前端按钮保存中禁用
- 保存前检查当前节点最近笔记中是否已存在相同或高度相似内容

### 风险 2 - 摘要质量差

问题：

- 前端本地总结可能不够自然

守门策略：

- 第一版采用“结构化提取”，不伪装高质量 AI 总结
- 第二版如有需要再引入后端总结接口

### 风险 3 - 笔记内容过长

问题：

- 聊天内容过长，保存后影响笔记页阅读体验

守门策略：

- 限制摘要长度
- 优先抽取最近几轮有效消息
- 保留“查看原对话”留待后续版本，不在当前 Sprint 中加入

---

## Harness Hooks / 自动检查建议

### Hook A - GraphPage 改动后跑笔记相关测试

触发条件：

- 编辑 `frontend/src/pages/GraphPage.jsx`
- 编辑 `frontend/src/contexts/NoteContext.jsx`
- 编辑 `frontend/src/services/api.js`

执行：

```bash
cd frontend && npx vitest run src/pages/graph-note-actions.test.jsx --pool=threads
```

### Hook B - 新增 Markdown 笔记格式校验

目标：

- 避免保存函数输出空字符串或只保存标题

执行：

```bash
cd frontend && npx vitest run src/utils/noteFormatting.test.jsx --pool=threads
```

### Hook C - 防重复保存静态检查

目标：

- 如果出现第二个绕过 `noteActions.addNote` 的直接 notes API 调用，给出提醒

检查原则：

- UI 层应尽量只通过 `NoteContext` 保存笔记

---

## 测试计划

### 前端单元测试

新增建议：

| 测试文件 | 覆盖点 |
|------|------|
| `frontend/src/utils/noteFormatting.test.jsx` | 聊天摘要格式、解释笔记格式、空内容保护 |
| `frontend/src/pages/graph-note-actions.test.jsx` | 点击按钮是否触发 `noteActions.addNote` |
| `frontend/src/pages/graph-note-actions.test.jsx` | 保存中按钮禁用、防重复点击 |
| `frontend/src/pages/graph-note-actions.test.jsx` | 成功 toast / 失败 toast |

### 集成验证

手动验证清单：

1. 选择任一节点，发起 2-3 轮聊天。
2. 点击“总结并保存”。
3. 检查当前节点笔记区是否新增笔记。
4. 进入“我的学习 -> 笔记”，检查是否能看到对应笔记。
5. 展开一条核心内容解释，点击“保存到笔记”。
6. 重复点击同一个保存按钮，确认不会瞬间写入多条重复笔记。

### 测试脚本建议

新增：

```powershell
scripts/test_note_capture.ps1
```

脚本内容建议执行：

```powershell
cd frontend
npx vitest run src/utils/noteFormatting.test.jsx --pool=threads
npx vitest run src/pages/graph-note-actions.test.jsx --pool=threads
npx eslint src/pages/GraphPage.jsx src/contexts/NoteContext.jsx src/utils
```

---

## 验收标准

满足以下条件才算完成：

1. 聊天助手存在“总结并保存”入口，且真实写入笔记。
2. 核心内容解释存在“保存到笔记”入口，且真实写入笔记。
3. 保存成功和失败都有明确反馈。
4. 重复点击不会产生明显重复写入。
5. 新增测试和脚本可通过。

---

## 推荐执行顺序

1. 先做 `noteFormatting` 工具函数和测试。
2. 接入核心内容解释“一键保存到笔记”。
3. 接入聊天“总结并保存到笔记”。
4. 补防重复保存状态和 toast。
5. 整理测试脚本并跑通。

---

## 本次结论

这两个功能都适合按“小步快跑”的 Harness 方式推进：

- 第一版优先复用现有笔记基础设施
- 把保存入口统一到 `NoteContext`
- 用测试和脚本守住回归
- 如摘要质量不够，再在第二阶段加 AI 总结接口

这能让功能更快落地，同时不把系统复杂度一下子拉高。
