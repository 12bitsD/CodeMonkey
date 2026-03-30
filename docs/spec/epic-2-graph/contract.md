# Epic 2 API 契约

## 计划接口

### POST /api/plans

**认证**: 是

**Request:**
```json
{
  "title": "深度学习入门",
  "originalInput": "我想学深度学习",
  "targetNodeId": "n3",
  "nodes": [
    {
      "id": "n1",
      "name": "Python基础",
      "status": "unlearned",
      "x": 100,
      "y": 100,
      "why": "深度学习需要编程基础",
      "what": ["变量", "循环", "函数"],
      "mastery": ["能写深度学习代码"],
      "prompt": "学习Python基础语法...",
      "resources": [
        {"name": "Python教程", "url": "https://...", "reason": "入门推荐"}
      ],
      "isTarget": false,
      "domain": "编程"
    }
  ],
  "edges": [
    {"from_node": "n1", "to_node": "n2"}
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "p_xxx",
    "title": "深度学习入门",
    "progress": 0,
    "total": 5,
    "status": "active",
    "lastAccess": "刚刚",
    "createdAt": "2026-03-30T12:00:00Z"
  }
}
```

---

### GET /api/plans

**认证**: 是

**Query Params:**
- `status`: `active` | `archived` (可选)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "p_xxx",
      "title": "深度学习入门",
      "progress": 3,
      "total": 5,
      "status": "active",
      "lastAccess": "刚刚",
      "createdAt": "2026-03-30T12:00:00Z"
    }
  ]
}
```

---

### GET /api/plans/{plan_id}/graph

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {
    "planId": "p_xxx",
    "title": "深度学习入门",
    "nodes": [
      {
        "id": "n1",
        "name": "Python基础",
        "status": "unlearned",
        "x": 100,
        "y": 100,
        "why": "...",
        "what": ["变量", "循环"],
        "mastery": ["能写代码"],
        "prompt": "...",
        "resources": [],
        "isTarget": false,
        "domain": "编程"
      }
    ],
    "edges": [
      {"from_node": "n1", "to_node": "n2"}
    ]
  }
}
```

---

### PUT /api/plans/{plan_id}

**认证**: 是

**Request:**
```json
{
  "title": "深度学习入门 (修订版)"
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

### PUT /api/plans/{plan_id}/archive

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {}
}
```

---

### PUT /api/plans/{plan_id}/restore

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {}
}
```

---

### DELETE /api/plans/{plan_id}

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {}
}
```

---

## 节点接口

### PUT /api/plans/{plan_id}/nodes/{node_id}/status

**认证**: 是

**Request:**
```json
{
  "status": "learned"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "nodeId": "n1",
    "status": "learned",
    "plan": {
      "progress": 4,
      "total": 5
    }
  }
}
```

**副作用:**
1. 更新 `nodes.status`
2. 更新 `plans.progress`
3. 插入 `learning_sessions` 记录
4. 若 status='learned': 将节点名称添加到 `user_profiles.mastered_knowledge`

---

### PUT /api/plans/{plan_id}/nodes/{node_id}/position

**认证**: 是

**Request:**
```json
{
  "x": 200,
  "y": 150
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

### PUT /api/plans/{plan_id}/nodes/positions

**认证**: 是

**Request:**
```json
{
  "positions": [
    {"nodeId": "n1", "x": 100, "y": 100},
    {"nodeId": "n2", "x": 200, "y": 150}
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "updated": 2
  }
}
```

---

## 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `PLAN_NOT_FOUND` | 404 | 计划不存在 |
| `NODE_NOT_FOUND` | 404 | 节点不存在 |
| `FORBIDDEN` | 403 | 无权访问该计划 |
| `PLAN_NOT_ARCHIVED` | 400 | 计划未处于归档状态 |
