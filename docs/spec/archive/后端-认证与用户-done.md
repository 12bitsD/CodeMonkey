# 后端接口规格 - 认证与用户

> 通用规范（错误码、响应格式等）见 [后端-通用规范.md](./后端-通用规范.md)

一致性标记：✅（接口路径/方法与实现一致；前端已对接 auth/user）

## 实现状态

**✅ 已实现并有测试覆盖（对齐代码现状，2026-01-26）**

- 所有5个API接口已实现
- 已存在认证与用户相关测试（见 backend/tests）
- 路由链路：/api/auth/* 与 /api/user/profile 与 spec 一致 ✅
- JWT 认证机制已实现（token 有效期 7 天）

## 接口清单

| 方法 | 路由 | 说明 | 契约需认证 | 当前实现需认证 | 状态 | 代码 |
|------|------|------|------------|----------------|------|------|
| POST | `/api/auth/register` | 用户注册 | ❌ | ❌ | ✅ | [auth.py](file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/backend/routers/auth.py#L22-L99) |
| POST | `/api/auth/login` | 用户登录 | ❌ | ❌ | ✅ | [auth.py](file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/backend/routers/auth.py#L101-L133) |
| POST | `/api/auth/logout` | 用户登出 | ✅ | ✅ | ✅ | [auth.py](file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/backend/routers/auth.py#L135-L143) |
| GET | `/api/user/profile` | 获取画像 | ✅ | ✅ | ✅ | [user.py](file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/backend/routers/user.py#L12-L49) |
| PUT | `/api/user/profile` | 更新画像 | ✅ | ✅ | ✅ | [user.py](file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/backend/routers/user.py#L52-L132) |

---

## 功能概述（说人话）

这个模块处理用户账号和个人画像：

| API | 一句话说明 |
|-----|-----------|
| 注册 | 用户填邮箱密码创建账号，同时给他创建一个空的画像 |
| 登录 | 验证邮箱密码，给他一个登录凭证(token) |
| 登出 | 让当前登录凭证失效 |
| 获取画像 | 拿到用户的背景信息（职业、教育、能力标签、已掌握知识） |
| 更新画像 | 用户手动修改自己的背景信息 |

**关于"已掌握知识"**：这个字段是只读的，用户不能手动改，只有当用户在图谱页把节点标记为"已学习"时，系统自动往这里添加。

---

## 接口详情

### 1. 注册

**做什么**：用户填邮箱密码，我们给他创建账号。创建账号的同时，也给他创建一个空的画像记录。

```
POST /api/auth/register
```

**请求**：
```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

**成功**：
```json
{
  "success": true,
  "data": {
    "user": { "id": "u_xxx", "email": "user@example.com" },
    "token": "jwt_token_xxx"
  }
}
```

**失败情况**：
- 邮箱格式不对 → 400 `INVALID_EMAIL`
- 密码太短（<6位）→ 400 `WEAK_PASSWORD`
- 邮箱已被注册 → 409 `EMAIL_EXISTS`

---

### 2. 登录

**做什么**：验证邮箱密码，返回登录凭证。

```
POST /api/auth/login
```

**请求**：
```json
{
  "email": "user@example.com",
  "password": "123456"
}
```

**成功**：
```json
{
  "success": true,
  "data": {
    "user": { "id": "u_xxx", "email": "user@example.com" },
    "token": "jwt_token_xxx",
    "expiresIn": 604800
  }
}
```

**失败情况**：
- 邮箱或密码错 → 401 `INVALID_CREDENTIALS`

---

### 3. 登出

**做什么**：让当前token失效。

```
POST /api/auth/logout
```

**请求头**：`Authorization: Bearer <token>`

**成功**：
```json
{ "success": true, "message": "已登出" }
```

**失败情况**：
- 未登录 / 未携带token / token无效 → 401 `UNAUTHORIZED`

---

### 4. 获取用户画像

**做什么**：返回用户的背景信息，用于首页显示能力标签、图谱生成时参考。

```
GET /api/user/profile
```

**请求头**：`Authorization: Bearer <token>`

**成功**：
```json
{
  "success": true,
  "data": {
    "occupation": "大三计算机学生",
    "education": "香港理工大学 计算机",
    "programmingLevel": "入门",
    "mathLevel": "入门",
    "abilities": [
      "Python 会基础语法和pandas",
      "线性代数 只记得矩阵乘法"
    ],
    "masteredKnowledge": [
      "矩阵乘法",
      "前向传播"
    ]
  }
}
```

**失败情况**：
- 未登录 / 未携带token / token无效 → 401 `UNAUTHORIZED`

**字段说明**：
| 字段 | 说明 | 来源 |
|------|------|------|
| occupation | 职业/身份 | 用户手动填 |
| education | 教育背景 | 用户手动填 |
| programmingLevel | 编程基础 | 用户选择：无基础/入门/熟练 |
| mathLevel | 数学基础 | 用户选择：无基础/入门/熟练 |
| abilities | 能力标签 | 用户手动添加 + AI从输入中提取 |
| masteredKnowledge | 已掌握知识 | **系统自动生成**，只读 |

---

### 5. 更新用户画像

**做什么**：用户在"我的学习-画像"页面修改自己的信息。

```
PUT /api/user/profile
```

**请求头**：`Authorization: Bearer <token>`

**请求**（只传要改的字段）：
```json
{
  "occupation": "大四计算机学生",
  "abilities": [
    "Python 熟练使用pandas和numpy",
    "JavaScript 会React开发"
  ]
}
```

**成功**：返回更新后的完整画像

**注意**：`masteredKnowledge` 字段会被忽略，用户不能直接改这个。

**失败情况**：
- 未登录 / 未携带token / token无效 → 401 `UNAUTHORIZED`

---


```sql
-- 当前实现：SQLite3（见 backend/database.py）
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE NOT NULL,
  occupation TEXT,
  education TEXT,
  programming_level TEXT DEFAULT '入门',
  math_level TEXT DEFAULT '入门',
  abilities TEXT DEFAULT '[]',
  mastered_knowledge TEXT DEFAULT '[]',
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## 实现方案

### 技术栈
- **框架**: FastAPI 0.109.0
- **数据库**: SQLite3 (原生SQL，无ORM)
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt (passlib)
- **测试**: pytest + httpx

### 文件结构
```
backend/
├── routers/
│   ├── auth.py          # 认证API实现 ✅ (2026-01-18)
│   └── user.py          # 用户画像API实现 ✅ (2026-01-18)
├── utils/
│   ├── __init__.py      # 工具包初始化 ✅ (2026-01-18)
│   ├── auth.py          # JWT工具函数 ✅ (2026-01-18)
│   ├── password.py      # 密码加密工具 ✅ (2026-01-18)
│   └── id_generator.py  # ID生成工具 ✅ (2026-01-18)
├── tests/
│   ├── test_auth.py     # 认证测试(10个) ✅ (2026-01-18)
│   └── test_user.py     # 用户测试(10个) ✅ (2026-01-18)
├── database.py          # 数据库管理(已添加user_profiles表) ✅ (2026-01-18)
├── models.py            # Pydantic模型(已添加认证模型) ✅ (2026-01-18)
└── main.py              # 应用入口(已注册auth和user路由) ✅ (2026-01-18)
```

### 关键实现细节

1. **注册流程**: 创建用户的同时自动创建空画像记录（包含默认的 programmingLevel 和 mathLevel）
2. **错误处理**: 使用JSONResponse返回统一格式的错误响应（包含success和error字段）
3. **认证机制**: JWT token，有效期7天，使用 HS256 算法，通过HTTPBearer验证
4. **密码安全**: 使用 bcrypt 算法加密密码，密码最短长度为6位
5. **邮箱验证**: 使用正则表达式验证邮箱格式，在业务逻辑层进行验证
6. **画像只读字段**: masteredKnowledge字段在update_profile中被忽略，保持只读
7. **测试隔离**: 每个测试运行前删除并重建测试数据库，确保测试独立性
8. **JSON存储**: abilities 和 masteredKnowledge 字段使用 JSON 格式存储在 SQLite 的 TEXT 字段中

### 测试覆盖
✅ 用户注册成功  
✅ 邮箱格式验证  
✅ 密码长度验证  
✅ 重复邮箱检测  
✅ 用户登录成功  
✅ 密码错误处理  
✅ 邮箱不存在处理  
✅ 用户登出  
✅ 无token登出处理  
✅ 注册时自动创建画像  
✅ 获取用户画像  
✅ 无认证获取画像  
✅ 更新职业  
✅ 更新教育背景  
✅ 更新编程水平  
✅ 更新数学水平  
✅ 更新能力标签  
✅ 批量更新多个字段  
✅ masteredKnowledge只读验证  
✅ 无认证更新画像
