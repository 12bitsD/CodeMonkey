# Epic 4 API 契约

## AI 接口

### POST /api/ai/parse-goal

**认证**: 是

**Request:**
```json
{
  "input": "我想学深度学习",
  "userBackground": {
    "occupation": "软件工程师",
    "education": "本科",
    "programmingLevel": "熟练",
    "mathLevel": "入门",
    "abilities": ["Python", "Java"],
    "masteredKnowledge": ["变量", "循环"]
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "interpretation": "用户想要系统学习深度学习，包括理论知识和实践技能",
    "backgroundSummary": [
      {"text": "有 Python 基础", "source": "abilities", "isStrength": true},
      {"text": "数学基础较弱", "source": "mathLevel", "isStrength": false}
    ],
    "suggestedNodeCount": 8,
    "shouldSplit": false,
    "splitSuggestions": null
  }
}
```

---

### POST /api/ai/generate-graph

**认证**: 是

**Request:**
```json
{
  "input": "我想学深度学习",
  "interpretation": "用户想要系统学习深度学习...",
  "userBackground": {...}
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "interpretation": "...",
    "nodes": [
      {
        "id": "n1",
        "name": "Python基础",
        "status": "unlearned",
        "x": 100,
        "y": 100,
        "why": "深度学习需要编程基础",
        "what": ["变量", "数据类型", "函数"],
        "mastery": ["能独立编写Python代码"],
        "prompt": "学习Python基础...",
        "resources": [
          {"name": "Python官方教程", "url": "https://...", "reason": "官方文档"}
        ],
        "isTarget": false,
        "domain": "编程"
      }
    ],
    "edges": [
      {"from_node": "n1", "to_node": "n2"}
    ],
    "targetNodeId": "n5"
  }
}
```

---

### POST /api/ai/clarify-goal

**认证**: 是

**Request:**
```json
{
  "originalGoal": "我想学深度学习",
  "newGoal": "我只想了解深度学习的基本概念，不做研究",
  "planId": "p_xxx"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "interpretation": "用户想要简化目标...",
    "isLargeChange": false,
    "suggestion": "可以删除数学推导相关节点...",
    "reason": "...",
    "changes": {
      "keep": ["n1", "n2", "n3"],
      "remove": ["n4", "n5"],
      "add": []
    }
  }
}
```

---

### POST /api/ai/recommend-next

**认证**: 是

**Request:**
```json
{
  "planId": "p_xxx"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "recommendedNodeId": "n3",
    "reason": "你已经掌握了 n1 和 n2，n3 依赖已满足且是关键节点"
  }
}
```

---

### POST /api/plans/{plan_id}/apply-changes

**认证**: 是

**Request:**
```json
{
  "newGoal": "深度学习基础",
  "keep": ["n1", "n2", "n3"],
  "remove": ["n4", "n5"],
  "add": [
    {
      "name": "新节点",
      "status": "unlearned",
      "x": 300,
      "y": 200,
      "why": "...",
      "what": [],
      "mastery": [],
      "prompt": "...",
      "resources": [],
      "isTarget": false
    }
  ],
  "newEdges": [
    {"from_node": "n2", "to_node": "n_new"}
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "planId": "p_xxx",
    "removedNodes": 2,
    "addedNodes": 1,
    "updatedTitle": "深度学习基础"
  }
}
```

---

## 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `AI_SERVICE_ERROR` | 500 | AI 服务调用失败 |
| `AI_TIMEOUT` | 504 | AI 服务超时 |
| `GOAL_TOO_VAGUE` | 400 | 学习目标过于模糊 |
