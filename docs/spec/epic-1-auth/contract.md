# Epic 1 API 契约

## 认证接口

### POST /api/auth/register

**认证**: 否

**Request:**
```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "u_xxx"
    },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

**Error (400):**
```json
{
  "success": false,
  "error": {
    "code": "EMAIL_EXISTS",
    "message": "邮箱已被注册"
  }
}
```

---

### POST /api/auth/login

**认证**: 否

**Request:**
```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "u_xxx"
    },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

**Error (401):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "邮箱或密码错误"
  }
}
```

---

### POST /api/auth/logout

**认证**: 是

**Request:** (空 body)

**Response (200):**
```json
{
  "success": true,
  "data": {}
}
```

---

## 用户画像接口

### GET /api/user/profile

**认证**: 是

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "occupation": "软件工程师",
    "education": "本科",
    "programmingLevel": "熟练",
    "mathLevel": "入门",
    "abilities": ["Python", "JavaScript"],
    "masteredKnowledge": ["变量", "循环"]
  }
}
```

---

### PUT /api/user/profile

**认证**: 是

**Headers:**
```
Authorization: Bearer <token>
```

**Request:** (所有字段可选)
```json
{
  "occupation": "产品经理",
  "education": "硕士",
  "programmingLevel": "入门",
  "mathLevel": "熟练",
  "abilities": ["产品设计", "数据分析"]
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "occupation": "产品经理",
    "education": "硕士",
    "programmingLevel": "入门",
    "mathLevel": "熟练",
    "abilities": ["产品设计", "数据分析"],
    "masteredKnowledge": []
  }
}
```

---

## 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `EMAIL_EXISTS` | 400 | 邮箱已被注册 |
| `INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 |
| `INVALID_EMAIL` | 400 | 邮箱格式不正确 |
| `WEAK_PASSWORD` | 400 | 密码强度不足 |
| `UNAUTHORIZED` | 401 | 未登录或 token 无效 |
