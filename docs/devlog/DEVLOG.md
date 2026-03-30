# DEVLOG — ConceptTree 开发日志

> 最新在最上方。每个 session 提炼关键决策，不复制粘贴实现细节。
> 完整 session 文件 → `archive/`

---

## 2026-03-30 架构重构 — bitsNovels 模式采纳

### 改了什么
- 将 `backend/models.py` 拆分为 `epic_N/models.py` (N=1..5)
- 文档目录重组：`docs/spec/` (Epic 规格) / `docs/design/` (架构约束) / `docs/devlog/` (工作日志) / `docs/archive/` (历史)
- 测试目录重组：`backend/tests/epic_N/` (按 Epic 归类)
- 删除 14 个冗余文档

### 为什么
- bitsNovels 架构模式要求代码和测试按 Epic 严格分区
- 便于定位：改某个功能时只要看对应 epic_N/

### 架构状态 (重组后)
- models.py: ✅ 拆分到 epic_N/models.py
- routers/: ❌ 仍在 root (未拆分)
- services/: ❌ 仍在 root (未拆分)
- 注意: 此次重构仅完成了 models 的 epic_N 分离

### 技术债
- routers/ services/ utils/ 未按 epic_N 分离
- 153 个需数据库的测试未运行 (DATABASE_URL 未配置)

## 2026-03-18 文档整理与目录重组

### 改了什么
- 将 `docs/` 按读者身份重新分层：`spec/`（AI必读合同）/ `architecture/`（人类读设计文档）/ `devlog/`（session 日志）
- 新建 `docs/spec/CLAUDE.md`：提炼 AI session 需要的全部边界信息（stack、约束、patterns）
- 将 8 个 `*-done.md` 移到 `spec/archive/`；状态统一在 `进度总览.md` 模块状态表维护
- 将架构文档（PRD、Architecture.md、AI服务Mermaid图、变更日志）移到 `architecture/`
- 将日期命名的 session 报告和 superpowers 文件移到 `devlog/archive/`
- 重写 `进度总览.md`：顶部加模块状态表，删除正文中零散状态描述

### 为什么
- 文档越来越多，AI 每次 session 无法判断哪些需要读
- 文件名承载状态（`-done.md` 后缀）导致 spec/ 文件增殖，实际上只需要在表格里维护状态
- PRD、架构图等叙述性文档不应该每次喂给 AI，按需注入更省 context

### 技术债
- `后端-通用规范.md` 中的代码引用链接使用了 `file://` 绝对路径，跨机器会失效，改为相对路径更好
- spec/ 中仍有少量过时描述（如"待完善功能"表的历史划线记录），下一次整理可清除

### 下次 session 需要知道的事
- spec/ 只有 4 个文件：`CLAUDE.md`（入口）、`进度总览.md`、`后端-通用规范.md`、`前端-架构总览.md`
- 新增功能时先更新 `进度总览.md` 模块状态表，完成后把对应 spec 文件移到 `archive/`
- architecture/ 里有 PRD，需要对齐需求时去那里找

---

## 2026-03-18 项目代码审查 + 文件整理

### 改了什么
- 全面审查前端/后端/AI服务代码，对照 PRD 核查完成度
- 清理根目录垃圾文件：删除 `.DS_Store`（16个）、`test_ai.db`、`test_simple.db`、`.pytest_cache`、`.ruff_cache`、`.sisyphus`、根目录误放的 `node_modules/package.json`
- 删除 `.node_runtime/`、`.trae/documents/`（AI 工作临时文档）
- 将 `test_api_manual.py` 移至 `backend/tests/manual/`
- 将 `ConceptTree/spec/*` 所有文件移至 `docs/spec/`（统一归档）
- 更新 `docs/spec/进度总览.md` 和 `docs/spec/前端-架构总览.md`，Phase 11 标记为已完成

### 为什么
- Phase 11（图谱交互补全）实际代码已全部实现，但文档仍标记为 ⏳ 未实现，造成误判
- spec/ 文件原在 `ConceptTree/spec/`，不是文档目录，归并到 `docs/spec/` 更清晰

### 关键发现
- GraphPage.jsx 中 Phase 11 全部已实现：双击(189行)、用于链接(500行)、保存按钮(194行)、离开弹窗(209行)、完成庆祝(397行)
- AI 服务代码质量高：4个核心功能完整，LLM 降级/重试机制完整，Prompt JSON 配置化
- 后端 26 个 API 全部实现，无遗漏

### 技术债
- `routers/user.py` 和 `tests/unit/test_ai_service_recommend_next.py` 有 LSP 类型错误（pyright 静态分析问题，运行时无影响）

---

## 2026-03-18 Phase 6–11 完成

### 改了什么
- **Phase 6**: 新增 `learning_history.py` + `/api/ai/recommend-next` 端点；前端接入 AI 推荐
- **Phase 7**: 修复 clarify-goal 不传节点上下文的 bug；新增 `POST /api/plans/{id}/apply-changes`；前端小幅调整走 apply-changes，大幅变化引导新建
- **Phase 8**: MasteryChecklist.jsx + ResourceList.jsx；搜索更多资源按钮；前端组件测试（jsdom）
- **Phase 9**: 笔记 Tab 计划筛选/分组/精准跳转（`?node=` URL参数）/删除；GraphPage ?node= 自动高亮
- **Phase 10**: `calculateProgress()` 工具函数；节点标记后首页进度即时刷新（AppContext 同步）；画像编程/数学基础下拉
- **Phase 11**: 双击切换节点状态；"用于"链接跳转；保存计划按钮+状态机；离开未保存弹窗；推荐浮层完成态

### 为什么
- Phase 7 关键修复：clarify-goal 之前不传节点 ID，导致 AI 无法产出有意义的 keep/remove diff（返回名字匹配而非精确 ID）
- Phase 9 精准跳转：URL 参数 `?node=` 解决了笔记页点击后图谱页无法定位节点的问题

### 技术债
- unit tests 中有几个 Pylance 类型警告（`.data` 访问 `Optional` 字段未判 None），运行时正常但静态分析报错

---

## 2026-03-17 Phase 1–5 完成

### 改了什么
- **Phase 1**: LLM Prompt 从 `.txt` 迁移到 `services/llm/configs/*.json`，支持非代码调参
- **Phase 2**: Vitest + Playwright 测试基础设施；共 6 个单元测试 + 5 个 E2E 测试
- **Phase 3**: GraphPage 节点状态/位置变更调用后端 API 持久化
- **Phase 4**: ToastContext + useToast；替换全部 `alert()` 和沉默 `console.error`
- **Phase 5**:
  - Chunk 1: 全局 Toast 系统
  - Chunk 2: user_background 全链路（前端 → 后端 → AI Service → Prompt {{background}}）
  - Chunk 3: clarify-goal 后端端点（`/api/ai/clarify-goal`）+ 前端 Modal UI

### 为什么
- Prompt JSON 化：LLM 调参频繁，代码分离后无需 redeploy 就能修改 Prompt
- user_background 全链路：PRD 要求图谱生成时根据用户背景自适应节点粒度，此前一直是 None

### 下次 session 需要知道的事（当时）
- Phase 6 起点：recommend-next 需要学习历史 → 需要先建 `learning_sessions` 查询服务

---

## 2026-01-27 后端对齐 Supabase

### 改了什么
- 数据库从本地 SQLite 迁移至 Supabase（PostgreSQL）
- 统一 `?` 占位符（`database.py` 自动转 `%s`）
- 执行 `supabase/migrations/initial_schema.sql`

### 为什么
- SQLite 不支持多用户并发，需要迁移到云端 DB 才能正式上线

### 技术债（已解决）
- `database.py` 的 `_convert_placeholders` 方案虽然 hack，但已稳定运行

---

## 2026-01-26 初始对齐

### 改了什么
- 创建 `docs/spec/` 目录，建立后端/前端各模块 Spec 文件
- 核对鉴权状态：plans/graph/notes/stats/ai 全部接入 JWT 鉴权和多用户隔离

### 技术债（已解决）
- 部分接口 edges 字段映射缺口 → Phase 2 解决（前端 api.js 双向映射）
