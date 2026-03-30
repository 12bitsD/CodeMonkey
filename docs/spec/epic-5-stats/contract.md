# Epic 5 API 契约

## 统计接口

### GET /api/stats/overview

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {
    "activePlans": 3,
    "completedPlans": 1,
    "masteredKnowledgeCount": 15,
    "notesCount": 8,
    "weeklyActivity": 4
  }
}
```

---

### GET /api/stats/distribution

**认证**: 是

**Response (200):**
```json
{
  "success": true,
  "data": {
    "distributions": [
      {
        "domain": "编程",
        "learned": 5,
        "total": 8,
        "percentage": 62.5
      },
      {
        "domain": "数学",
        "learned": 2,
        "total": 10,
        "percentage": 20
      },
      {
        "domain": "深度学习",
        "learned": 3,
        "total": 5,
        "percentage": 60
      }
    ]
  }
}
```

---

## 计算方式

### weeklyActivity
统计 `learning_sessions` 表中，最近 7 天有学习记录的天数

### distribution.percentage
```
percentage = (learned / total) * 100
保留 1 位小数
```
