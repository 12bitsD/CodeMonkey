# ConceptTree — Harness Engineering 更新计划
> 基于 ROADMAP.md，通过 Claude Code hooks + 自动化行为驱动每个 Sprint 的执行与质量保证  
> 生成日期：2026-04-14

---

## 核心策略

```
Harness = Hooks (PreToolUse / PostToolUse / UserPromptSubmit / Stop)
        + 自动行为 (settings.json automated behaviors)
        + 定时任务 (CronCreate scheduled agents)
```

用 harness 做三件事：
1. **守门**：阻止危险操作（写 .env、暴露 secret）
2. **自动验**：每次代码变更后自动跑安全检查 / 测试 / lint
3. **提醒**：在正确时机提示下一步动作

---

## Sprint 执行顺序 × Harness 激活时间线

```
Day 1-2  [Sprint 0]  激活 Hook 1(.env 拦截) + Hook 2(SQL 检查) + JWT 检查
Week 1-2 [Sprint 1]  激活 Hook 3(bandit) + Hook 4(auth 测试) + 每日漏洞扫描 Cron
Week 3-5 [Sprint 2]  激活 Hook 5(ruff+mypy) + Hook 6(ESLint) + Hook 7(SSE 检查)
Week 6-8 [Sprint 3]  激活 Hook 8(Prompt 校验) + Hook 9(Stop 提醒)
持续     [Sprint 4]  激活每周性能基线 Cron
```

---

## Sprint 0 — 紧急安全修复（Day 1-2）

**对应 ROADMAP：S1、S2、L1**

### 代码任务

| 任务 | 文件 | 状态 |
|------|------|------|
| 创建 .env.example，将 .env 加入 .gitignore | `backend/.gitignore` | ⬜ |
| 轮换所有凭据（DB密码、JWT secret、API key） | `backend/.env` | ⬜ |
| database.py schema 名白名单验证，消除 SQL 拼接 | `backend/database.py:53` | ⬜ |
| auth.py 使用 config.py 的 JWT_SECRET_KEY 和 JWT_EXPIRE_DAYS | `backend/utils/auth.py:10,12` | ⬜ |

### Hook 1 — PreToolUse：阻止向 .env 写入内容

```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; d=json.load(sys.stdin); p=d.get(\\\"file_path\\\",\\\"\\\"); sys.exit(1 if \\\".env\\\" in p and \\\".env.example\\\" not in p else 0)\"'",
          "blocking": true,
          "onBlockMessage": "阻止写入 .env 文件。凭据请写入 .env.example（去掉真实值），真实 .env 由运维手动管理。"
        }
      ]
    }
  ]
}
```

### Hook 2 — PostToolUse：编辑 database.py 后检查 SQL 拼接

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -q \"database.py\"; then grep -n \"f\\\"\\|f\\'\\|% \" \"$FILE\" && echo \"⚠️ 发现字符串格式化拼入 SQL，请检查\" || echo \"✅ database.py 无直接 SQL 拼接\"; fi'"
        }
      ]
      
    }
  ]
}
```

### UserPromptSubmit Hook — 检查 JWT 硬编码

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'grep -r \"SECRET_KEY\\s*=\\s*[\\\"\\x27]\" backend/utils/ 2>/dev/null && echo \"⚠️ L1: auth.py 存在硬编码 JWT secret，需使用 config.py\" || true'"
        }
      ]
    }
  ]
}
```

---

## Sprint 1 — 安全加固（Week 1-2）

**对应 ROADMAP：S4、S5、S6、S7、S8、S9、S10、S12**

### 代码任务

| 任务 | 文件 | 状态 |
|------|------|------|
| 限制 CORS 为指定域名 | `backend/config.py:38-42` | ⬜ |
| 登录/注册加频率限制（slowapi，5次/15分钟） | `backend/routers/auth.py` | ⬜ |
| 统一错误响应，隐藏异常详情 | `backend/routers/plans.py:94-102` | ⬜ |
| JWT Token 黑名单（Redis 或内存 set） | `backend/routers/auth.py:136` | ⬜ |
| 密码强度要求：8位+复杂度 | `backend/routers/auth.py:35` | ⬜ |
| Notes 接口加 Pydantic 校验模型 | `backend/routers/notes.py:78,162` | ⬜ |
| 关闭生产环境 DEBUG 模式 | `backend/config.py:27` | ⬜ |
| 关闭生产环境 /docs | `backend/main.py` | ⬜ |

### Hook 3 — PostToolUse：bandit 安全扫描

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -q \"\\.py$\"; then cd backend && bandit -ll -q \"$FILE\" 2>/dev/null || echo \"⚠️ bandit 发现安全问题\"; fi'"
        }
      ]
    }
  ]
}
```

### Hook 4 — PostToolUse：auth.py 变更后跑测试

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -qE \"auth\\.py|config\\.py\"; then cd backend && python -m pytest tests/test_auth.py -x -q 2>/dev/null || echo \"⚠️ Auth 测试失败\"; fi'"
        }
      ]
    }
  ]
}
```

### 定时任务 — 每日依赖漏洞扫描

```
调度命令：cd backend && pip-audit --format=json
触发时间：每天 09:00
行为：发现漏洞时输出告警，列出依赖名和 CVE ID
```

---

## Sprint 2 — 核心学习体验升级（Week 3-5）

**对应 ROADMAP：F1、F3、F5**

### 代码任务

| 任务 | 文件 | 状态 |
|------|------|------|
| 澄清流程加入「学习目的」三选一 | `frontend/src/` | ⬜ |
| Prompt 接入 learning_purpose 参数 | `backend/services/` | ⬜ |
| Node 模型加入 phase / phase_order / depth_level 字段 | `backend/models.py` | ⬜ |
| DB schema 迁移：node 表新字段 | `backend/schema.sql` | ⬜ |
| Prompt 加入阶段分组逻辑 | prompt config JSON | ⬜ |
| 图谱页面阶段背景区域视觉呈现 | `frontend/src/` | ⬜ |
| 后端改为 SSE StreamingResponse 返回图谱节点 | `backend/routers/` | ⬜ |
| 前端接收 SSE 逐步渲染节点 | `frontend/src/` | ⬜ |

### Hook 5 — PostToolUse：ruff + mypy（后端）

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -q \"backend.*\\.py$\"; then ruff check \"$FILE\" --quiet && echo \"✅ ruff OK\" || echo \"⚠️ ruff 错误\"; mypy \"$FILE\" --ignore-missing-imports --quiet && echo \"✅ mypy OK\" || echo \"⚠️ mypy 类型错误\"; fi'"
        }
      ]
    }
  ]
}
```

### Hook 6 — PostToolUse：ESLint（前端）

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -qE \"\\.jsx?$|\\.tsx?$\"; then cd frontend && npx eslint \"$FILE\" --quiet && echo \"✅ ESLint OK\" || echo \"⚠️ ESLint 错误\"; fi'"
        }
      ]
    }
  ]
}
```

### Hook 7 — PostToolUse：SSE 接口用法检查

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -qE \"generate_graph|explain_topic|chat\"; then grep -q \"StreamingResponse\" \"$FILE\" && echo \"✅ SSE StreamingResponse 已配置\" || echo \"⚠️ 该 AI 接口未使用 StreamingResponse，F5 要求流式返回\"; fi'"
        }
      ]
    }
  ]
}
```

---

## Sprint 3 — AI 深度内容 + 聊天助手（Week 6-8）

**对应 ROADMAP：F2、F4、F6、F7**

### 代码任务

| 任务 | 文件 | 状态 |
|------|------|------|
| 新增 POST /api/ai/explain-topic（按层生成内容） | `backend/routers/ai.py` | ⬜ |
| 节点详情面板 what 条目变为可点击按钮 | `frontend/src/` | ⬜ |
| 点击后展开 AI 内容区域（带 loading 状态） | `frontend/src/` | ⬜ |
| 生成内容缓存写入 DB（content_cache 字段） | `backend/routers/` | ⬜ |
| 前端悬浮 AI 聊天按钮 + mini chat 窗口 UI | `frontend/src/` | ⬜ |
| 后端流式聊天接口 POST /api/ai/chat（SSE） | `backend/routers/ai.py` | ⬜ |
| 聊天回复「保存为笔记」功能 | `frontend/src/` | ⬜ |
| LLM 分级调用：图谱用 kimi-k2.5，节点用 moonshot-v1-8k | `backend/services/` | ⬜ |

### Hook 8 — PostToolUse：Prompt JSON 参数校验

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "bash -c 'FILE=$(echo \"$CLAUDE_TOOL_INPUT\" | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\"file_path\\\",\\\"\\\"))\"); if echo \"$FILE\" | grep -qE \"parse_goal|generate_graph\"; then python3 -c \"import json; d=json.load(open(\\\"$FILE\\\")); t=d.get(\\\"temperature\\\",0); mt=d.get(\\\"max_tokens\\\",0); w=[]; t>0.8 and w.append(f\\\"temperature={t} 偏高，建议≤0.7\\\"); mt<2000 and mt>0 and w.append(f\\\"max_tokens={mt} 偏小，建议≥2000\\\"); [print(f\\\"⚠️ Prompt: {x}\\\") for x in w]; not w and print(\\\"✅ Prompt 参数正常\\\")\" 2>/dev/null || true; fi'"
        }
      ]
    }
  ]
}
```

### Hook 9 — Stop：任务结束时提示更新 ROADMAP

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "echo '📋 提醒：本次修改是否需要更新 ROADMAP.md 中的任务状态？'"
        }
      ]
    }
  ]
}
```

---

## Sprint 4 — 持续优化（持续进行）

**对应 ROADMAP：S11、S13 及后期功能**

### 代码任务

| 任务 | 文件 | 状态 |
|------|------|------|
| Docker 容器非 root 用户运行（添加 USER 指令） | `backend/Dockerfile` | ⬜ |
| 添加安全响应头中间件（CSP、X-Frame-Options） | `backend/main.py` | ⬜ |
| 引入 psycopg2.pool 连接池 | `backend/database.py` | ⬜ |
| 前端 Context 拆分（PlanContext/NoteContext/GraphContext） | `frontend/src/contexts/` | ⬜ |

### 定时任务 — 每周性能基线检查

```
调度命令：
  检查 backend/ 是否引入连接池（psycopg2.pool）
  检查 frontend/src/contexts/ 是否已完成 Context 拆分
  对比 ROADMAP 五（性能优化）清单输出进度报告
触发时间：每周一 10:00
```

---

## 完整 settings.json 结构

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "JWT 硬编码检查命令"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".env 写入拦截命令",
            "blocking": true,
            "onBlockMessage": "阻止写入 .env 文件。"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "SQL 拼接检测（database.py）" },
          { "type": "command", "command": "bandit 安全扫描（.py）" },
          { "type": "command", "command": "auth 测试（auth.py/config.py）" },
          { "type": "command", "command": "ruff + mypy（backend .py）" },
          { "type": "command", "command": "ESLint（.jsx/.tsx）" },
          { "type": "command", "command": "SSE 用法检查（AI 接口）" },
          { "type": "command", "command": "Prompt 参数校验（JSON config）" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "echo 'ROADMAP 更新提醒'" }
        ]
      }
    ]
  }
}
```

---

## 架构变更摘要（来自 ROADMAP 三）

### 新增数据字段

```
Node 模型新增：
  - phase: str          # 所属阶段名（"地基" / "核心" / "应用"）
  - phase_order: int    # 阶段排序
  - depth_level: int    # 该节点需生成几层内容（1-4，由学习目的决定）
  - content_cache: json # 各层已生成内容缓存 {1: "...", 2: "...", 3: "..."}

Plan 模型新增：
  - learning_purpose: str  # "explore" / "apply" / "master"
```

### 新增 API 接口

```
POST /api/ai/explain-topic   # 按需生成节点某一层内容
POST /api/ai/chat            # 聊天助手（流式，SSE）
POST /api/ai/generate-graph  # 改为 SSE 流式响应
```

---

## 设计原则（不能偏离）

1. **系统负责校准深度** — 用户选目的，系统决定内容深度
2. **按需生成** — 内容在用户需要时才生成，不预加载全部
3. **深度优于广度** — 宁可少几个节点，每个节点要讲透
4. **速度是体验的一部分** — 任何 AI 调用都要有即时反馈（loading、streaming）
