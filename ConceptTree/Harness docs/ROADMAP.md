# ConceptTree 改进计划

> 网站：http://codemonkey666.space  
> 核心理念：**深度直达，不走弯路** — 过完所有节点 = 刚好学会，不多不少  
> 目标用户：学生、想快速上手一门知识/技能的人  
> 更新日期：2026-04-13

---

## 一、需要改进的完整 List

### 🔴 安全问题（Security）

| # | 问题 | 位置 | 优先级 | 备注 |
|---|------|------|--------|------|
| S1 | `.env` 含真实密码/API Key 已提交 GitHub，需轮换所有凭据 + 加入 `.gitignore` | `backend/.env` | CRITICAL | ⚠️ 需立即处理 |
| S2 | SQL 注入：schema 名直接拼入 SQL | `backend/database.py:53` | CRITICAL | PostgreSQL不支持参数化schema，需白名单验证 |
| S3 | SQL 注入：UPDATE 动态列名拼接 | `backend/routers/user.py:110` | ~~CRITICAL~~ → LOW | ✅ **非注入**：列名来自代码白名单，非用户输入 |
| S4 | CORS 允许 `*` 且同时开启 credentials | `backend/config.py:38-42` | HIGH | ⚠️ 默认 `CORS_ORIGINS="*"` + `CORS_ALLOW_CREDENTIALS=True` |
| S5 | 登录/注册接口无频率限制，可暴力破解 | `backend/routers/auth.py` | HIGH | ⚠️ 无 slowapi |
| S6 | 异常信息直接返回给前端，泄露内部结构 | `backend/routers/plans.py:94-102` | HIGH | ⚠️ `str(e)` 直接返回 |
| S7 | 退出登录不使 JWT 失效（无 Token 黑名单） | `backend/routers/auth.py:136` | HIGH | ⚠️ logout 是空操作 |
| S8 | 最低密码长度仅 6 位 | `backend/routers/auth.py:35` | HIGH | ⚠️ 仅检查长度，无复杂度 |
| S9 | Notes 接口接受原始 `dict`，无 Pydantic 校验 | `backend/routers/notes.py:78,162` | HIGH | ⚠️ `body: dict` 三处使用 |
| S10 | DEBUG 模式默认开启 | `backend/config.py:27` | MEDIUM | ⚠️ `_get_bool_env("DEBUG", True)` |
| S11 | Docker 容器以 root 用户运行 | `backend/Dockerfile` | MEDIUM | ⚠️ 无 `USER` 指令 |
| S12 | 生产环境 `/docs` OpenAPI 接口未关闭 | `backend/main.py` | MEDIUM | ⚠️ 无环境判断关闭 |
| S13 | 无安全响应头（CSP、X-Frame-Options 等） | `backend/main.py` | LOW | ⚠️ 无中间件 |
| S14 | 无审计日志（登录、数据修改无记录） | 全局 | LOW | ⚠️ 无敏感操作日志 |

### ⚠️ 补充发现：配置脱节

| # | 问题 | 位置 | 优先级 | 说明 |
|---|------|------|--------|------|
| L1 | JWT 配置未生效 | `backend/utils/auth.py:10,12` | **HIGH** | 硬编码 `SECRET_KEY` 和 `ACCESS_TOKEN_EXPIRE_DAYS`，未使用 `config.py` 中的 `JWT_SECRET_KEY` 和 `JWT_EXPIRE_DAYS` |

---

### 🟦 功能改进（Features）

#### F1 — 澄清流程升级：加入「学习目的」
- 现有流程：目标识别 + 背景分析 → 确认
- 新增第三步：用户选择学习目的（单选）
  - `了解这个领域` → 系统生成认知层 + 理解层内容
  - `项目/工作中能用` → 认知 + 理解 + 应用层
  - `系统精通` → 全4层（含内化/自测）
- 学习目的作为参数传入图谱生成，校准节点深度和数量

#### F2 — 节点内容 4 层模型
- 每个节点内部拆分为 4 个可展开层级：
  1. **认知层**：这是什么？为什么存在？（1-2 段）
  2. **理解层**：它怎么工作？（原理 + 类比）
  3. **应用层**：怎么用？（代码示例 + 实际场景）
  4. **内化层**：自测问题（能否解释给别人听？）
- 内容按需生成（点击层级时调用 AI），结果缓存避免重复请求
- 生成风格：纯文字讲解为主，可含代码示例

#### F3 — 图谱阶段分组（Phase Grouping）
- AI 生成图谱时自动将节点归入阶段（地基 → 核心 → 应用等）
- DAG 保持可拖动，阶段用半透明背景色区域标注
- 节点上显示阶段标签（小 badge）
- 新增 `phase` 字段到节点数据模型

#### F4 — 悬浮 AI 助手聊天窗口
- 右下角悬浮按钮，点击展开 mini chat
- 系统上下文：当前学习目标 + 所有节点（朝专精方向做深入）
- 当前打开的节点自动作为对话焦点
- 会话不跨页面保存；用户可手动点击「保存为笔记」将 AI 回复存到对应节点
- 输入框支持 Enter 发送

#### F5 — 图谱生成流式输出（Streaming）
- 后端使用 SSE（Server-Sent Events）流式返回节点
- 前端边接收边渲染：节点逐个出现，用户不用等全部完成
- 解决「输入目标 → 等待 → 看到结果」的长等待感

#### F6 — LLM 分级调用优化（速度优化）
- 图谱生成（复杂）：保持 `kimi-k2.5`，加 streaming 改善体验
- 节点内容按需生成（中等）：考虑用更快的 `moonshot-v1-8k`
- 聊天助手（轻量）：用最快模型，优先响应速度
- 对已生成内容做缓存，相同节点+层级不重复调用 LLM

#### F7 — 核心内容可交互（已有 what 字段升级）
- 节点详情面板中，`what` 列表每条变为可点击按钮
- 点击后在右侧展开 AI 生成的详细内容（对应 F2 的层级）
- 生成内容自动关联到该节点的笔记，可手动编辑保存

---

## 二、更新计划表

### Sprint 0 — 紧急修复（1-2天）
> 目标：修复最严重的安全和配置问题

| 任务 | 对应 | 预计复杂度 |
|------|------|-----------|
| 删除 `.env` 文件，轮换所有凭据 | S1 | 低 |
| `.env` 加入 `.gitignore`，从 git 历史清除 | S1 | 低 |
| 修复 `database.py` schema SQL 注入（白名单验证） | S2 | 低 |
| 修复 `auth.py` 使用 `config.py` 的 JWT 配置 | L1 | 低 |

---

### Sprint 1 — 安全加固（1-2 周）
> 目标：消除所有 CRITICAL 和 HIGH 安全风险，上线安全

| 任务 | 对应 | 预计复杂度 |
|------|------|-----------|
| 限制 CORS 为指定域名，关闭 wildcard credentials | S4 | 低 |
| 登录/注册加频率限制（slowapi，5次/15分钟） | S5 | 低 |
| 统一错误响应，隐藏异常详情 | S6 | 低 |
| JWT Token 黑名单（退出登录真正失效） | S7 | 中 |
| 密码强度要求提升至 8 位+复杂度 | S8 | 低 |
| Notes 接口加 Pydantic 校验 | S9 | 低 |
| 关闭生产环境 DEBUG 模式 | S10 | 低 |
| 关闭生产环境 `/docs` | S12 | 低 |

---

### Sprint 2 — 核心学习体验升级（2-3 周）
> 目标：解决用户反馈的 3 个核心痛点（慢、粗、无法深入）

| 任务 | 对应 | 预计复杂度 |
|------|------|-----------|
| 澄清流程加入「学习目的」三选一 | F1 | 中 |
| 图谱生成 Prompt 接入学习目的参数，校准深度和节点数 | F1 | 中 |
| 节点数据模型加入 `phase` 字段 | F3 | 低 |
| 图谱生成 Prompt 加入阶段分组逻辑 | F3 | 中 |
| 图谱页面阶段背景区域视觉呈现 | F3 | 中 |
| 后端 SSE 流式返回图谱节点 | F5 | 中高 |
| 前端接收 SSE 逐步渲染节点 | F5 | 中高 |

---

### Sprint 3 — AI 深度内容 + 聊天助手（2-3 周）
> 目标：实现「点击即深入」和「随时提问」

| 任务 | 对应 | 预计复杂度 |
|------|------|-----------|
| 新增后端接口 `/api/ai/explain-topic`（按层生成内容） | F2/F7 | 中 |
| 节点详情面板 `what` 条目变为可点击按钮 | F7 | 低 |
| 点击后展开 AI 内容区域（带 loading 状态） | F7 | 中 |
| 生成内容缓存机制（DB 存储，避免重复请求） | F6 | 中 |
| 前端悬浮 AI 聊天按钮 + mini chat 窗口 UI | F4 | 中 |
| 后端流式聊天接口（带节点上下文） | F4 | 中 |
| 聊天回复「保存为笔记」功能 | F4 | 低 |
| LLM 调用分级：不同任务用不同速度模型 | F6 | 中 |

---

### Sprint 4 — 打磨与优化（持续）
> 目标：细节体验提升，为更多用户做准备

| 任务 | 对应 | 预计复杂度 |
|------|------|-----------|
| Docker 容器非 root 用户运行 | S11 | 低 |
| 添加安全响应头中间件 | S13 | 低 |
| 节点「手动拆分」功能（一个节点 → 2-4 子节点） | 后期 | 高 |
| 掌握验证小测验（标记已学时 AI 出题） | 后期 | 高 |

---

## 三、架构变更摘要

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
POST /api/ai/generate-graph  # 改为 SSE 流式响应（保持 POST，通过 StreamingResponse）
```

---

## 四、链路设计问题（需修复）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| L1 | JWT 配置未生效 | `backend/utils/auth.py` | 硬编码 secret/过期时间，未使用 config.py |
| L2 | AppContext.nodes 不一致 | `frontend/src/contexts/AppContext.jsx` | `plansApi.list/create` 返回 plan 无 nodes，但 AppContext 假设存在 |
| L3 | 恢复归档链路错误 | `frontend/src/pages/MyLearningPage.jsx` | 用 `updatePlan({status:'active'})` 而非 `plansApi.restore()` |
| L4 | API 无版本控制 | 全局 | 建议后续引入 `/api/v1/` 前缀 |

---

## 五、性能优化

| 层级 | 问题 | 建议 |
|------|------|------|
| 后端 | 无连接池 | 引入 `psycopg2.pool` |
| 后端 | 无 LLM 缓存 | 引入缓存层（Redis/内存） |
| 后端 | 大图谱无分页 | 分页+索引优化 |
| 前端 | Context 过重 | 拆分为 PlanContext/NoteContext/GraphContext |
| 前端 | Graph 无虚拟化 | 50+ 节点时考虑视口裁剪 |

---

## 六、Prompt 优化

| Config | 问题 | 建议 |
|--------|------|------|
| `parse_goal.json` | temperature=1 太高 | 降至 0.7 |
| `parse_goal.json` | max_tokens=800 太小 | 增至 2000 |
| `parse_goal.json` | 无 learning_purpose | 注入学习目的参数 |
| `generate_graph.json` | 无 phase 分组 | 添加阶段分组规则 |
| `generate_graph.json` | 5-12 节点范围太大 | 按 learning_purpose 调整 |
| `generate_graph.json` | 无 depth_level | 指定内容深度 |

---

## 七、设计原则（不能偏离）

1. **系统负责校准深度** — 用户选目的，系统决定内容深度，不让用户做多余决策
2. **按需生成** — 内容在用户需要时才生成，不预加载全部
3. **深度优于广度** — 宁可少几个节点，每个节点要讲透
4. **速度是体验的一部分** — 任何 AI 调用都要有即时反馈（loading、streaming）
