# Epic 3: 前端需求

## 页面: 我的学习 (`/my-learning`)

### Tab: 笔记

**US-3.2 查看笔记列表**
- 按计划分组显示
- 显示笔记内容预览
- 显示关联节点名称
- 显示创建时间

**US-3.4 删除笔记**
- 删除按钮
- 确认弹窗

### 组件

```
MyLearningPage
├── Tabs
│   ├── Plans (计划)
│   ├── Notes (笔记) ←
│   ├── Profile (画像)
│   └── Stats (统计)
└── NotesTab
    ├── PlanFilter (下拉筛选)
    ├── NoteCard (循环)
    │   ├── NodeName
    │   ├── ContentPreview
    │   ├── Date
    │   └── DeleteButton
    └── EmptyState
```

---

## 节点详情面板

**US-3.1 创建笔记** (在 GraphPage 节点详情中)

```
NodeDetailPanel
├── NotesSection
│   ├── NoteList
│   │   └── NoteItem (循环)
│   │       ├── Content
│   │       └── DeleteButton
│   ├── AddNoteButton
│   └── NoteEditor (点击后显示)
│       ├── Textarea
│       ├── SaveButton
│       └── CancelButton
```

---

## API 调用

```javascript
// 获取笔记
notesApi.list(planId)  // planId 可选

// 创建笔记
notesApi.create(planId, nodeId, content)

// 更新笔记
notesApi.update(noteId, content)

// 删除笔记
notesApi.delete(noteId)
```
