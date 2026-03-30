# Epic 3 API 契约

## 笔记接口

### POST /api/notes

**认证**: 是

**Request:**
```json
{
  "planId": "p_xxx",
  "nodeId": "n1",
  "content": "# 学习心得\n\n今天学习了变量..."
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "note_xxx",
    "planId": "p_xxx",
    "nodeId": "n1",
    "content": "# 学习心得...",
    "date": "刚刚",
    "createdAt": "2026-03-30T12:00:00Z"
  }
}
```

---

### GET /api/notes

**认证**: 是

**Query Params:**
- `planId`: `p_xxx` (可选)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "note_xxx",
      "planId": "p_xxx",
      "nodeId": "n1",
      "content": "# 学习心得...",
      "date": "3月30日",
      "createdAt": "2026-03-30T12:00:00Z"
    }
  ]
}
```

---

### PUT /api/notes/{note_id}

**认证**: 是

**Request:**
```json
{
  "content": "# 更新后的心得..."
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {}
}
```

---

### DELETE /api/notes/{note_id}

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {}
}
```

---

## 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `NOTE_NOT_FOUND` | 404 | 笔记不存在 |
| `FORBIDDEN` | 403 | 无权操作该笔记 |
| `CONTENT_REQUIRED` | 400 | 内容不能为空 |
