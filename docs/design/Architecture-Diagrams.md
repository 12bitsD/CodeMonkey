# ConceptTree 系统架构图

> **一句话总结**：AI驱动的学习路径生成器，将学习目标转化为可视化知识图谱，支持进度追踪和笔记管理。

---

## 图1：宏观系统架构（L1）

```mermaid
flowchart TB
    subgraph Client["客户端"]
        Browser["用户浏览器"]
    end

    subgraph Frontend["前端层 (React + Vite)"]
        Router["React Router"]
        Pages["页面组件"]
        Context["状态管理 (Context API)"]
        Services["API 服务层"]
    end

    subgraph Backend["后端层 (FastAPI)"]
        Routers["API 路由 (7个模块)"]
        Services_BE["业务服务"]
        Utils["工具函数"]
    end

    subgraph Data["数据层"]
        Postgres["PostgreSQL (Supabase)"]
        LocalStorage["LocalStorage (前端缓存)"]
    end

    subgraph AI["AI服务"]
        LLM["LLM API (规划中)"]
    end

    Browser -->|HTTP| Router
    Router --> Pages
    Pages --> Context
    Context --> Services
    Services -->|/api/*| Routers
    Routers --> Services_BE
    Services_BE --> Utils
    Routers --> Postgres
    Services -->|fallback| LocalStorage
    Routers -->|mock| LLM
```

### 说人话
用户打开浏览器 → 前端React应用加载 → 根据URL显示不同页面 → 需要数据时调用后端API → 后端FastAPI处理请求 → 操作PostgreSQL数据库 → 返回数据给前端显示。

---

## 图2：前端架构（L2）

### 2.1 路由结构

```mermaid
flowchart LR
    subgraph Routes["路由表 (App.jsx)"]
        R1["/"<br/>首页]
        R2["/auth"<br/>登录/注册]
        R3["/graph/:planId"<br/>图谱页]
        R4["/my-learning"<br/>我的学习]
    end

    subgraph Protected["需要登录"]
        P1[GraphPage]
        P2[MyLearningPage]
    end

    R3 -->|ProtectedRoute| P1
    R4 -->|ProtectedRoute| P2
```

### 说人话
- **首页** (`/`)：输入学习目标，显示进行中的计划
- **认证页** (`/auth`)：登录和注册
- **图谱页** (`/graph/:planId`)：显示知识图谱画布（需登录）
- **我的学习** (`/my-learning`)：归档计划、画像、笔记、统计（需登录）

---

### 2.2 状态管理架构

```mermaid
flowchart TB
    subgraph Providers["Context Providers"]
        Auth["AuthContext<br/>认证状态 + Token"]
        App["AppContext<br/>业务数据"]
    end

    subgraph AuthState["AuthContext 状态"]
        A1["user: {id, email}"]
        A2["isAuthenticated: boolean"]
        A3["token: string"]
    end

    subgraph AppState["AppContext 状态"]
        S1["userProfile: 用户画像"]
        S2["plans: 学习计划列表"]
        S3["allNotes: 笔记列表"]
        S4["isLoading: boolean"]
    end

    subgraph Actions["暴露的 Actions"]
        AC1["setUserProfile()"]
        AC2["createPlan()"]
        AC3["updatePlan()"]
        AC4["archivePlan()"]
        AC5["addNote()"]
    end

    Auth --> AuthState
    App --> AppState
    App --> Actions
```

### 说人话
- **AuthContext**：管登录状态，存token，判断用户是否登录
- **AppContext**：管业务数据，包括用户画像、学习计划、笔记等
- 页面通过 `useContext` 获取数据和操作函数

---

### 2.3 API 服务层（Hybrid策略）

```mermaid
flowchart LR
    subgraph API["services/api.js"]
        AuthAPI["authApi<br/>✅ 真实后端"]
        UserAPI["userProfileApi<br/>✅ 真实后端"]
        PlansAPI["plansApi<br/>⚠️ List真实/Create Mock"]
        GraphAPI["graphApi<br/>⚠️ Get真实/Generate Mock"]
        NotesAPI["notesApi<br/>❌ LocalStorage Mock"]
        AIAPI["aiApi<br/>❌ Mock"]
    end

    subgraph Backend["后端接口"]
        B1["/auth/*"]
        B2["/user/profile"]
        B3["/plans"]
        B4["/plans/{id}/graph"]
    end

    AuthAPI --> B1
    UserAPI --> B2
    PlansAPI --> B3
    GraphAPI --> B4
```

### 说人话
前端API层采用"混合策略"：
- **已完成对接**：认证、用户画像、计划列表、图谱获取
- **部分Mock**：计划创建、图谱生成
- **后端完成前端未对接**：笔记、统计（后端已实现，前端仍为LocalStorage Mock）
- **完全Mock**：AI解析（后端为Mock实现）

### 关键对齐缺口
| 缺口 | 后端字段 | 前端期望 | 影响 |
|------|---------|---------|------|
| edges字段 | `from_node`/`to_node` | `from`/`to` | 图谱连线可能失败 |
| createPlan参数 | 需`originalInput`/`targetNodeId` | 未传 | 创建计划可能失败 |

---

## 图3：后端架构（L2）

### 3.1 API 路由结构

```mermaid
flowchart TB
    subgraph FastAPI["FastAPI (main.py)"]
        Entry["/api"]
    end

    subgraph Routers["路由模块 (7个)"]
        R_AUTH["/auth<br/>认证"]
        R_USER["/user<br/>用户"]
        R_PLANS["/plans<br/>计划"]
        R_GRAPH["/plans/{id}/graph<br/>图谱"]
        R_NOTES["/notes<br/>笔记"]
        R_STATS["/stats<br/>统计"]
        R_AI["/ai<br/>AI服务"]
    end

    subgraph Endpoints["关键端点"]
        E1["POST /auth/login"]
        E2["POST /plans"]
        E3["GET /plans/{id}/graph"]
        E4["PUT /nodes/{id}/status"]
        E5["POST /ai/parse-goal"]
    end

    Entry --> Routers
    R_AUTH --> E1
    R_PLANS --> E2
    R_GRAPH --> E3
    R_GRAPH --> E4
    R_AI --> E5
```

### 说人话
后端有7个路由模块，共26个接口：
- **认证** (`/auth`)：注册、登录、登出
- **用户** (`/user`)：获取/更新用户画像
- **计划** (`/plans`)：CRUD + 归档/恢复
- **图谱** (`/plans/{id}/graph`)：获取图谱、更新节点状态/位置
- **笔记** (`/notes`)：CRUD
- **统计** (`/stats`)：学习统计、领域分布
- **AI** (`/ai`)：目标解析、图谱生成（当前Mock）

---

### 3.2 数据库模型（ER图）

```mermaid
erDiagram
    users ||--|| user_profiles : has
    users ||--o{ plans : owns
    users ||--o{ learning_sessions : has
    plans ||--o{ nodes : contains
    plans ||--o{ edges : contains
    nodes ||--o{ notes : has
    nodes ||--o{ learning_sessions : recorded_in

    users {
        string id PK
        string email UK
        string password_hash
        timestamp created_at
    }

    user_profiles {
        string id PK
        string user_id FK
        string occupation
        string education
        string programming_level
        string math_level
        jsonb abilities
        jsonb mastered_knowledge
        timestamp updated_at
    }

    plans {
        string id PK
        string user_id FK
        string title
        string original_input
        string target_node_id
        int progress
        int total
        string status
        timestamp last_access_at
        timestamp created_at
    }

    nodes {
        string id PK
        string plan_id FK
        string name
        string status
        float x
        float y
        string why
        jsonb what
        jsonb mastery
        string prompt
        jsonb resources
        boolean is_target
        string domain
    }

    edges {
        string id PK
        string plan_id FK
        string from_node_id FK
        string to_node_id FK
    }

    notes {
        string id PK
        string plan_id FK
        string node_id FK
        string user_id FK
        text content
        timestamp created_at
        timestamp updated_at
    }

    learning_sessions {
        string id PK
        string user_id FK
        string plan_id FK
        string node_id FK
        string node_name
        string action
        timestamp created_at
    }
```

### 说人话
- **users**：用户账号（邮箱、密码）
- **user_profiles**：用户画像（职业、教育背景、能力标签）
- **plans**：学习计划（标题、进度、状态）
- **nodes**：知识节点（名称、状态、坐标、学习内容）
- **edges**：节点间的依赖关系
- **notes**：用户对节点的笔记
- **learning_sessions**：学习记录（用于统计和推荐）

---

## 图4：数据流架构（L2）

### 4.1 用户登录流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端
    participant DB as 数据库

    U->>F: 输入邮箱密码
    F->>B: POST /api/auth/login
    B->>DB: 查询用户
    DB-->>B: 用户数据
    B->>B: 验证密码
    B->>B: 生成JWT Token
    B-->>F: {user, token}
    F->>F: localStorage存储token
    F->>F: AuthContext更新状态
    F->>B: GET /user/profile
    B-->>F: 用户画像
    F->>F: AppContext加载数据
    F-->>U: 跳转到首页
```

### 4.2 创建学习计划流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端
    participant DB as 数据库

    U->>F: 输入学习目标
    F->>F: 显示确认弹窗
    U->>F: 确认生成
    F->>B: POST /api/ai/parse-goal
    B-->>F: 解析结果
    F->>B: POST /api/ai/generate-graph
    B-->>F: 图谱数据
    F->>B: POST /api/plans
    B->>DB: 插入plan/nodes/edges
    DB-->>B: 确认
    B-->>F: planId
    F-->>U: 跳转到图谱页
```

### 4.3 更新节点状态流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端
    participant DB as 数据库

    U->>F: 点击"标记已学习"
    F->>B: PUT /api/plans/{id}/nodes/{id}/status
    B->>DB: 更新node状态
    B->>DB: 更新plan进度统计
    B->>DB: 插入learning_session
    alt 状态为learned
        B->>DB: 更新user_profiles.mastered_knowledge
    end
    DB-->>B: 确认
    B-->>F: {nodeId, status, plan}
    F->>F: 更新本地状态
    F-->>U: 更新UI显示
```

---

## 图5：关键模块依赖关系（L3）

### 5.1 后端模块依赖

```mermaid
flowchart TB
    subgraph Main["main.py"]
        M1["FastAPI App"]
        M2["全局异常处理"]
        M3["CORS配置"]
    end

    subgraph Routers_DEPS["路由层"]
        R1["auth.py"]
        R2["user.py"]
        R3["plans.py"]
        R4["graph.py"]
        R5["notes.py"]
        R6["stats.py"]
        R7["ai.py"]
    end

    subgraph Utils["工具层"]
        U1["auth.py<br/>JWT处理"]
        U2["password.py<br/>密码哈希"]
        U3["id_generator.py<br/>ID生成"]
    end

    subgraph DB["数据层"]
        D1["database.py<br/>连接管理"]
        D2["models.py<br/>Pydantic模型"]
    end

    M1 --> Routers_DEPS
    R1 --> U1
    R1 --> U2
    R3 --> U1
    R4 --> U1
    R5 --> U1
    R6 --> U1
    R7 --> U1
    Routers_DEPS --> D1
    Routers_DEPS --> D2
```

---

### 5.2 前端模块依赖

```mermaid
flowchart TB
    subgraph Entry["入口"]
        E1["main.jsx"]
        E2["App.jsx"]
    end

    subgraph Contexts["状态层"]
        C1["AuthContext.jsx"]
        C2["AppContext.jsx"]
    end

    subgraph Pages["页面层"]
        P1["HomePage.jsx"]
        P2["AuthPage.jsx"]
        P3["GraphPage.jsx"]
        P4["MyLearningPage.jsx"]
    end

    subgraph Services["服务层"]
        S1["api.js"]
        S2["config/api.js"]
    end

    subgraph Components["组件层"]
        CO1["ProtectedRoute.jsx"]
        CO2["UI组件"]
    end

    E1 --> E2
    E2 --> Contexts
    E2 --> Pages
    Contexts --> Services
    Pages --> Contexts
    Pages --> Components
    P3 --> CO1
    P4 --> CO1
```

---

## 图6：部署架构（L2）

```mermaid
flowchart TB
    subgraph Client["用户端"]
        Browser["浏览器"]
    end

    subgraph DevEnvironment["开发环境"]
        Vite["Vite Dev Server<br/>(localhost:3000)"]
        FastAPI["FastAPI<br/>(localhost:8000)"]
    end

    subgraph Production["生产环境（规划中）"]
        CDN["静态资源 CDN"]
        Server["FastAPI Server"]
        DB["Supabase PostgreSQL"]
    end

    Browser -->|开发模式| Vite
    Vite -->|/api proxy| FastAPI
    FastAPI -->|SQL| DB
    Browser -->|生产模式| CDN
    CDN --> Server
    Server --> DB
```

### 说人话
- **开发**：前端Vite（3000端口）→ 代理到后端FastAPI（8000端口）→ Supabase数据库
- **生产**：前端静态资源部署到CDN，后端部署到服务器，共用Supabase数据库

---

## 关键文件速查表

| 层级 | 文件 | 作用 |
|------|------|------|
| **入口** | `ConceptTree/frontend/src/main.jsx` | 前端入口 |
| **入口** | `ConceptTree/frontend/src/App.jsx` | 路由配置 |
| **入口** | `ConceptTree/backend/main.py` | 后端入口 |
| **状态** | `ConceptTree/frontend/src/contexts/AuthContext.jsx` | 认证状态 |
| **状态** | `ConceptTree/frontend/src/contexts/AppContext.jsx` | 业务状态 |
| **API** | `ConceptTree/frontend/src/services/api.js` | API封装 |
| **路由** | `ConceptTree/backend/routers/auth.py` | 认证路由 |
| **路由** | `ConceptTree/backend/routers/plans.py` | 计划路由 |
| **路由** | `ConceptTree/backend/routers/graph.py` | 图谱路由 |
| **模型** | `ConceptTree/backend/epic_N/models.py` (N=1..5) | Epic 各自的 Pydantic 模型 |
| **模型(facade)** | `ConceptTree/backend/models.py` | Pydantic facade (re-exports from epic_N/models.py) |
| **数据库** | `ConceptTree/backend/database.py` | 数据库连接 |

---

