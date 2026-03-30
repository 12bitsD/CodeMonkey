# Epic 1: 前端需求

## 页面: 认证页 (`/auth`)

### 功能

**US-1.1 注册**
- 邮箱输入框
- 密码输入框 (>= 6 位)
- 确认密码输入框
- 注册按钮
- 错误提示 (邮箱格式/密码太短/邮箱已注册)

**US-1.2 登录**
- 邮箱输入框
- 密码输入框
- 登录按钮
- 错误提示 (凭证错误)

### 交互

1. 未登录用户访问 → 显示 AuthPage
2. 已登录用户访问 `/auth` → 自动跳转首页 `/`
3. 注册/登录成功 → 存储 token → 跳转首页

### 组件

```
AuthPage
├── AuthCard
│   ├── Tab: 登录 / 注册
│   ├── EmailInput (FormInput)
│   ├── PasswordInput (FormInput)
│   ├── ConfirmPasswordInput (注册时显示)
│   ├── SubmitButton (LoadingButton)
│   └── ErrorAlert (错误时显示)
└── SuccessView (成功时显示)
```

### 状态

- `isLoading`: 提交中
- `error`: 错误信息
- `isLoginMode`: 是否登录模式

### API 调用

```javascript
// 注册
authApi.register(email, password)

// 登录
authApi.login(email, password)

// 登出
authApi.logout()
```

---

## 页面: 首页 (`/`)

### 功能

**US-1.4 查看画像**
- 头像/邮箱显示
- 画像下拉 (编程水平/数学水平)

**US-1.5 更新画像**
- 编辑个人信息
- 保存后更新 AppContext

### 画像下拉

```
用户名 ▼
├── 我的画像
├── 编程基础: [入门 ▼]
├── 数学基础: [入门 ▼]
└── 登出
```

### 组件

```
HomePage
├── Header
│   ├── Logo
│   ├── NavLinks
│   └── UserMenu (AuthContext)
│       ├── Avatar
│       └── Dropdown
│           ├── ProfileEditor
│           │   ├── OccupationInput
│           │   ├── EducationInput
│           │   ├── ProgrammingLevelSelect
│           │   ├── MathLevelSelect
│           │   └── SaveButton
│           └── LogoutButton
```

### API 调用

```javascript
// 获取画像
userProfileApi.get()

// 更新画像
userProfileApi.update({
  occupation,
  education,
  programmingLevel,
  mathLevel,
  abilities
})
```
