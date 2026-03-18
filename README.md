<p align="center">
  <img src="https://img.shields.io/badge/由-100%25%20AI%20构建-blueviolet?style=for-the-badge" alt="由 AI 构建">
  <img src="https://img.shields.io/badge/由-AI%20智能体维护-success?style=for-the-badge" alt="由 AI 维护">
  <img src="https://img.shields.io/badge/人类代码-0%25-lightgrey?style=for-the-badge" alt="人类代码 0%">
</p>

<h1 align="center">
  <br>
  <img src="https://api.iconify.design/fluent-emoji:brain.svg" width="80" alt="ConceptTree Logo">
  <br>
  ConceptTree
  <br>
</h1>

<h4 align="center">
  🧠 AI 驱动的学习路径生成器 — 由 AI 构建与维护
</h4>

<p align="center">
  <em>输入你想学的内容，获得知识依赖图谱，一个节点一个节点地掌握任何知识。</em>
</p>

---

## 🤖 这个项目不一样

**没有人类写过这些代码。**

这个项目的全部内容——从架构设计到具体实现——都由 AI 智能体创建和维护。代码结构、命名规范、文档，甚至这份 README，都是为 AI 理解和修改而优化的。

> "当 AI 为 AI 构建时，一切都变成了规范。"

---

## 🎯 ConceptTree 是什么？

ConceptTree 是一个**学习路径生成器**，能将任何学习目标转化为带有清晰依赖关系的可视化知识图谱。

**输入：** `"我想理解深度学习中的反向传播，我会 Python 但数学不太好"`

**输出：** 一张漂亮的交互式知识图谱，清晰展示你需要学什么、按什么顺序学、配套资源和检验标准。

<p align="center">
  <img src="https://api.iconify.design/fluent-emoji:world-map.svg" width="60">
</p>

### 核心功能

| 功能             | 描述                                             |
| ---------------- | ------------------------------------------------ |
| **智能目标解析** | AI 分析你的输入，提取学习目标和已有知识背景      |
| **知识图谱生成** | 创建精确到公式级别的依赖感知学习路径             |
| **自适应学习**   | 根据你的背景跳过已掌握的内容                     |
| **进度追踪**     | 每个节点的可视化进度：`未学习 → 已学习 → 已掌握` |
| **个人笔记**     | 为每个知识节点附加 Markdown 笔记                 |
| **资源推荐**     | 为每个概念精选学习材料                           |

---

## 🏗️ 架构哲学

这个代码库遵循一个原则：**AI 优先的可维护性**。

## 📚 文档入口

| 文档 | 说明 |
|------|------|
| [进度总览.md](./ConceptTree/spec/进度总览.md) | MVP 完成状态一览 |
| [后端-通用规范.md](./ConceptTree/spec/后端-通用规范.md) | 后端契约与通用约定 |
| [前端-架构总览.md](./ConceptTree/spec/前端-架构总览.md) | 前端架构与 API 策略 |
| [变更日志.md](./ConceptTree/spec/变更日志.md) | Spec 变更历史 |
| [学习路径规划器 - MVP PRD（最终版）.md](./学习路径规划器%20-%20MVP%20PRD（最终版）.md) | 需求文档（PRD） |

```
📁 ConceptTree/
├── 📁 spec/                   ← 真理之源。AI 首先读这里。
│   ├── 进度总览.md             ← MVP 完成状态（活跃）
│   ├── 后端-通用规范.md         ← 后端契约（活跃）
│   ├── 前端-架构总览.md         ← 前端架构（活跃）
│   ├── 变更日志.md             ← 变更历史（活跃）
│   └── *-done.md              ← 已完成模块（归档）
├── 📁 backend/                ← FastAPI 应用
│   ├── routers/               ← API 端点
│   ├── services/              ← 业务逻辑
│   ├── utils/                 ← 通用能力
│   └── tests/                 ← 测试
└── 📁 frontend/               ← React + Vite 应用
    ├── pages/                 ← 路由组件
    ├── components/            ← 可复用 UI
    ├── services/              ← API 客户端
    ├── contexts/              ← 状态管理
    └── tests/                 ← 测试
```

### 为什么这样设计？

1. **规范先于代码** — 每个功能在实现前都会先写入 `/spec`。AI 先读规范，再写测试，最后写代码。

2. **扁平且明确** — 没有深层嵌套的文件夹。每个文件都有清晰、单一的职责。

3. **约定优于配置** — 命名模式严格且可预测。AI 可以从名称推断文件位置。

4. **测试驱动** — 测试即可执行的文档。AI 用测试验证自己的工作。

---

## 🚀 快速开始

### 1. 配置 LLM API Key

本项目使用 Kimi 2.5 (moonshot-v1-8k) 作为 AI 服务的大脑。请在 `ConceptTree/backend` 目录下创建 `.env` 文件：

```bash
cd ConceptTree/backend
cp .env.example .env
```

并在 `.env` 中填入你的 API Key：
```env
LLM_API_KEY=sk-your-kimi-api-key
```

### 2. 启动服务

```bash
# 一条命令启动前后端
./start-dev.sh
```

**就这样。** 前端运行在 `http://localhost:3000`，后端在 `http://localhost:8000`。

<details>
<summary>手动启动（如果你非要的话）</summary>

**后端：**

```bash
cd ConceptTree/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**前端：**

```bash
cd ConceptTree/frontend
npm install && npm run dev
```

</details>

---

## 🛠️ 技术栈

| 层级        | 技术                            |
| ----------- | ------------------------------- |
| **前端**    | React 18 + Vite + Tailwind CSS  |
| **后端**    | FastAPI + Pydantic              |
| **数据库**  | SQLite (本地) / Supabase (云端) |
| **AI 集成** | LLM 驱动的目标解析与图谱生成    |

---

## 📜 开发规则

AI 智能体在修改代码库时遵循这些规则：

1. **写代码前先读 `/spec`**
2. **先更新规范，再写测试，最后实现**
3. **测试不通过不提交**
4. **在规范中标记实现状态** (`✅` / `❌`)
5. **保持真理之源同步**

这些规则定义在 `.trae/rules/project_rules.md` 中，由 AI 开发工作流强制执行。

## ✅ 文档同步机制（防止再次脱节）

- 后端接口变更后，必须同步更新 [后端-通用规范.md](file:///Users/bytedance/Desktop/CodeSpace/CodeMonkey/ConceptTree/spec/%E5%90%8E%E7%AB%AF-%E9%80%9A%E7%94%A8%E8%A7%84%E8%8C%83.md) 的“接口完整清单”表格
- 通过自动化校验确认 spec 与 OpenAPI 一致（无需数据库即可跑）：

```bash
cd ConceptTree/backend
python -m pytest -q test_docs_sync.py
```

---

## 🔮 路线图

- [ ] 完善认证机制（刷新/吊销/黑名单）
- [ ] 学习进度云同步
- [ ] 导出学习路径为可分享链接
- [ ] 移动端响应式图谱可视化
- [ ] 为每个知识节点集成 AI 导师

---

## 📊 项目状态

**MVP 进行中（最后更新：2026-03-18）**

| 组件               | 状态      | 备注                                                     |
| ------------------ | --------- | -------------------------------------------------------- |
| 核心图谱引擎       | ✅ 已完成 | 节点/边/状态/位置全持久化                               |
| 目标解析 AI        | ✅ 已完成 | 真实 Kimi 2.5，Prompt JSON 配置化                       |
| 个性化图谱         | ✅ 已完成 | user_background 全链路打通                              |
| 用户认证           | ✅ 已完成 | JWT + 注册/登录/登出                                    |
| 前端 UI            | ✅ 已完成 | 首页/图谱/我的学习，全局 Toast                          |
| 目标调整 (clarify) | ✅ 已完成 | clarify-goal 携带节点上下文，AI 返回精确 diff           |
| apply-changes      | ✅ 已完成 | 小幅调整直接修改图谱；大幅变化引导新建                  |
| AI 学习调度        | ✅ 已完成 | recommend-next：学习历史+画像+LLM；规则引擎兜底         |
| 测试覆盖           | ✅ 已完成 | Vitest 6 + Playwright 4 + 后端单元测试 9               |
| 节点详情展示       | ⏳ Phase 8 | mastery checklist + resources 列表（后端已生成）        |
| 笔记体验           | ⏳ Phase 9 | 按计划分组、筛选、精准跳转                              |
| 进度实时同步       | ⏳ Phase 10 | 图谱页学习后首页进度自动刷新                           |
| 云数据库           | 🔄 可选   | 当前 SQLite，可迁移至 Supabase                          |
| 移动端支持         | ⏳ 计划中 | 响应式适配                                              |

---

## 🤝 贡献指南

**想要贡献？** 有点不一样——你可以：

1. **提交规范** — 按 `/spec` 格式写功能规范，AI 会来实现
2. **直接写代码** — 传统 PR 欢迎，但请同步更新规范

记住：在这个仓库里，文档就是源代码。

---

## 📄 许可证

MIT 许可证 — 随便用，随便改，让你的 AI 在此基础上继续构建。

---

<p align="center">
  <sub>
    由 🤖 AI 构建，为想学任何东西的人类服务。
  </sub>
</p>
