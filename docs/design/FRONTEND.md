# 前端架构规范

## 项目结构

```
frontend/src/
├── App.jsx              # 根组件 + 路由
├── main.jsx             # 入口
├── index.css            # 全局样式
│
├── pages/               # 页面组件
│   ├── HomePage.jsx     # /
│   ├── AuthPage.jsx     # /auth
│   ├── GraphPage.jsx    # /graph/:planId
│   └── MyLearningPage.jsx # /my-learning
│
├── components/          # 组件
│   ├── ui/             # 基础 UI
│   │   ├── Button.jsx
│   │   ├── Modal.jsx
│   │   ├── Badge.jsx
│   │   └── LoadingButton.jsx
│   ├── common/         # 通用业务组件
│   │   ├── ProtectedRoute.jsx
│   │   ├── StatCard.jsx
│   │   ├── ChartBar.jsx
│   │   └── InfoSection.jsx
│   └── node/           # 节点相关
│       ├── MasteryChecklist.jsx
│       └── ResourceList.jsx
│
├── contexts/            # 状态管理
│   ├── AppContext.jsx   # 业务状态
│   ├── AuthContext.jsx  # 认证状态
│   └── ToastContext.jsx # Toast 通知
│
├── hooks/              # 自定义 Hooks
│   └── useGraphInteraction.js
│
├── services/           # API 层
│   └── api.js          # 统一后端调用入口
│
├── config/             # 配置
│   └── api.js          # API_BASE_URL
│
├── utils/              # 工具函数
│   └── progress.js     # 进度计算
│
└── types/              # 类型定义 (JSDoc)
    └── index.js
```

## 路由

| 路径 | 组件 | 认证 |
|------|------|------|
| `/` | HomePage | 否 |
| `/auth` | AuthPage | 否 (已登录跳转首页) |
| `/graph/:planId` | GraphPage | 是 |
| `/my-learning` | MyLearningPage | 是 |

## Context 职责

| Context | 状态 |
|---------|------|
| AppContext | userProfile, plans, allNotes, isLoading |
| AuthContext | user, token, isAuthenticated |
| ToastContext | toast.error(), toast.success() |

## API 层

- 入口: `services/api.js`
- 禁止: 组件内直接 fetch
- edges 映射: `mapEdgesFromBackend()` / `mapEdgesToBackend()`

## 状态管理原则

- **AppContext**: 计划/笔记/画像等业务数据
- **AuthContext**: token 和登录态
- **useState**: 局部 UI 状态 (loading, modal, 临时状态)

## 组件原则

1. 组件名: PascalCase
2. Props: 明确类型
3. 复杂逻辑: 提取为 custom hook
4. API 调用: 放在 services/api.js，组件只调用

## Toast 通知

所有错误/成功提示必须用 Toast:

```javascript
import { useToast } from '../contexts/ToastContext'
const toast = useToast()
toast.error('操作失败')
toast.success('已保存')
```
