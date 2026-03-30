# Epic 1: 认证与用户

## 用户故事

### US-1.1 用户注册
**作为** 访客  
**我想要** 注册账号  
**以便于** 使用学习功能

**验收标准 (AC)**:
- 邮箱格式正确
- 密码 >= 6 位
- 邮箱不重复
- 返回 JWT token
- 自动创建 user_profiles 记录

**API:** `POST /api/auth/register`

**业务逻辑**:
1. 验证邮箱格式
2. 验证密码强度 (>= 6 位)
3. 检查邮箱不重复
4. 密码哈希存储
5. 生成 JWT token (7 天有效)
6. 创建 user_profiles (默认空画像)

---

### US-1.2 用户登录
**作为** 访客  
**我想要** 登录账号  
**以便** 使用学习功能

**验收标准**:
- 邮箱密码正确
- 返回 JWT token

**API:** `POST /api/auth/login`

**业务逻辑**:
1. 查询用户 (邮箱)
2. 验证密码
3. 生成 JWT token

---

### US-1.3 用户登出
**作为** 登录用户  
**我想要** 登出  
**以便于** 清除会话

**API:** `POST /api/auth/logout`

**注意**: 当前实现仅删除前端 token，无 token 黑名单

---

### US-1.4 获取用户画像
**作为** 登录用户  
**我想要** 查看我的画像  
**以便于** 了解学习背景

**API:** `GET /api/user/profile`

**响应字段**:
- occupation: 职业
- education: 教育背景
- programmingLevel: 编程水平 (入门/熟练)
- mathLevel: 数学水平 (入门/熟练)
- abilities: 已掌握技能列表
- masteredKnowledge: 已掌握知识列表

---

### US-1.5 更新用户画像
**作为** 登录用户  
**我想要** 更新我的画像  
**以便于** 个性化学习

**API:** `PUT /api/user/profile`

**可更新字段** (全部可选):
- occupation
- education
- programmingLevel
- mathLevel
- abilities
- masteredKnowledge (由系统自动更新，不接受手动修改)

---

## 技术细节

### JWT 配置
- 算法: HS256
- 有效期: 7 天 (604800 秒)
- 存储: 前端 localStorage

### 密码哈希
- 算法: pbkdf2_sha256
- 库: passlib

### ID 生成
- 用户 ID 前缀: `u_`
- 画像 ID 前缀: `p_`
- 使用 UUID v4
