# 后端架构规范

## 项目结构

```
backend/
├── main.py              # FastAPI 入口
├── models.py            # Pydantic 模型 (统一导出)
├── database.py          # 数据库连接
├── config.py            # 配置
├── schema.sql          # 数据库 schema
│
├── routers/            # API 路由 (按类型)
│   ├── auth.py         # /api/auth/*
│   ├── user.py         # /api/user/*
│   ├── plans.py        # /api/plans/*
│   ├── graph.py        # /api/plans/{id}/graph
│   ├── notes.py        # /api/notes/*
│   ├── stats.py        # /api/stats/*
│   └── ai.py           # /api/ai/*
│
├── services/           # 业务逻辑
│   ├── ai_service.py   # AI 服务
│   ├── learning_history.py
│   └── llm/           # LLM 集成
│       ├── client.py
│       ├── providers/
│       └── configs/    # Prompt JSON 配置
│
└── tests/             # 测试 (按 epic_N 组织)
    ├── epic_1/
    ├── epic_2/
    ├── epic_3/
    ├── epic_4/
    ├── epic_5/
    └── global/
```

## 路由组织

| 路由文件 | 职责 | Epic |
|----------|------|------|
| auth.py | 注册/登录/登出 | epic-1 |
| user.py | 用户画像 | epic-1 |
| plans.py | 计划 CRUD | epic-2 |
| graph.py | 图谱操作 | epic-2 |
| notes.py | 笔记 CRUD | epic-3 |
| stats.py | 统计 | epic-5 |
| ai.py | AI 服务 | epic-4 |

## 数据库连接

- 库: psycopg2
- 占位符: `?` (database.py 自动转换为 `%s`)
- Schema: `schema.sql` 是唯一真相

## 认证

- 方式: JWT (HS256)
- 有效期: 7 天
- 获取: `get_current_user_id = Depends(HTTPBearer())`

## API 响应格式

```python
# 成功
{"success": True, "data": {...}}

# 失败
{"success": False, "error": {"code": "ERROR_CODE", "message": "..."}}
```

## 错误码

| 前缀 | 模块 |
|------|------|
| AUTH_* | 认证 |
| USER_* | 用户 |
| PLAN_* | 计划 |
| NODE_* | 节点 |
| NOTE_* | 笔记 |
| AI_* | AI 服务 |

## 新增接口流程

1. 在 `routers/` 对应文件添加路由
2. 在 `models.py` 添加 Pydantic 模型
3. 在 `main.py` 注册 router (如需)
4. 添加测试到 `tests/epic_N/`
5. 更新对应 Epic spec 文档
