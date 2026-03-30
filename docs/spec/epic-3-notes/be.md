# Epic 3: 笔记

## 用户故事

### US-3.1 创建笔记
**作为** 学习者  
**我想要** 为节点添加笔记  
**以便于** 记录学习心得

**API:** `POST /api/notes`

**AC**:
- planId, nodeId, content 必填
- content 不能为空
- 返回笔记 ID

---

### US-3.2 获取笔记列表
**作为** 学习者  
**我想要** 查看我的笔记  
**以便于** 回顾学习内容

**API:** `GET /api/notes`

**Query Params:**
- `planId`: 按计划筛选 (可选)

**AC**:
- 仅返回当前用户的笔记
- 按 created_at 降序排列

---

### US-3.3 更新笔记
**作为** 学习者  
**我想要** 修改笔记内容  
**以便于** 补充内容

**API:** `PUT /api/notes/{note_id}`

**AC**:
- 仅所有者可更新
- 更新 updated_at

---

### US-3.4 删除笔记
**作为** 学习者  
**我想要** 删除笔记  
**以便于** 清理不需要的内容

**API:** `DELETE /api/notes/{note_id}`

**AC**:
- 仅所有者可删除

---

## 笔记数据结构

```typescript
interface Note {
  id: string;         // "note_xxx"
  planId: string;
  nodeId: string;
  content: string;    // Markdown 格式
  date: string;        // 友好格式: "3月30日"
  createdAt: string;   // ISO 时间戳
}
```
