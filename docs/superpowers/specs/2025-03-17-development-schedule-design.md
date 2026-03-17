# ConceptTree MVP 开发 Schedule 设计文档

> **Approved Date**: 2025-03-17  
> **Strategy**: 方案 A（风险驱动）  
> **Target**: 全功能 MVP（后端零 Mock，AI 服务接真实 LLM）

---

## 1. 项目现状（Baseline）

### 1.1 后端状态（23/26 端点已实现）

| 模块 | 状态 | 关键偏差 |
|------|------|---------|
| 认证与用户 | ✅ 完成 | logout 无 token 黑名单 |
| 学习计划 | ✅ 完成 | edges 生成 `e_` 前缀 id |
| 图谱操作 | ✅ 完成 | edges 返回 `from_node/to_node` |
| 笔记 | ✅ 完成 | 搜索为 LIKE（非全文检索） |
| 统计 | ✅ 完成 | 无风险 |
| AI 服务 | ⚠️ Mock | `parse-goal` / `generate-graph` 为硬编码 |
| **未实现** | ❌ | `recommend-next` / `clarify-goal` / `apply-changes` |

### 1.2 前端对接状态

| 模块 | 后端状态 | 前端对接 | 实际情况 |
|------|---------|---------|---------|
| auth | ✅ | ✅ 真实 | token 存 localStorage |
| userProfile | ✅ | ✅ 真实 | 有 fallback |
| plans.list | ✅ | ✅ 真实 | 有 fallback |
| plans.create/update/archive/restore/delete | ✅ | ❌ Mock | **主链路断裂** |
| graph.get/status/position | ✅ | ✅ 真实 | edges 字段不匹配 |
| notes | ✅ | ❌ Mock | LocalStorage |
| stats | ✅ | ❌ 未对接 | 未调用 |
| AI | ⚠️ Mock | ❌ Mock | 两端 Mock |

---

## 2. 开发策略

**选择：方案 A（风险驱动）**

理由：
1. AI 服务的 Prompt 调优是唯一真正不确定的部分
2. 后端其他模块已全部就绪，Mock 清零是机械工作
3. 每个 Phase 有清晰的验收标准

---

## 3. Phase 详细设计

### Phase 1 — AI 服务接真实 LLM

**Duration**: 无硬性 deadline，按质量推进  
**Exit Criteria**: AI 接口返回真实解析结果

| # | 任务 | 文件 | 复杂度 | 风险点 |
|---|------|------|--------|--------|
| 1.1 | LLM Client 框架（OpenAI SDK 格式） | `backend/services/llm/client.py` | 🟡 中 | 无 |
| 1.2 | Kimi 2.5 配置 | `backend/config.py` | 🟢 低 | 无 |
| 1.3 | parse-goal Prompt + JSON Schema | `backend/services/llm/prompts/` | 🔴 高 | Prompt 调优反复 |
| 1.4 | generate-graph Prompt + JSON Schema | `backend/services/llm/prompts/` | 🔴 高 | 图谱质量不稳定 |
| 1.5 | 替换 ai_service.py Mock | `backend/services/ai_service.py` | 🟡 中 | 接口兼容 |
| 1.6 | 错误处理（超时/重试/降级） | `backend/services/llm/` | 🟡 中 | 无 |
| 1.7 | 集成测试 | `backend/tests/test_ai.py` | 🟡 中 | 需真实 API Key |

**技术要点**:
- Kimi 2.5 兼容 OpenAI SDK，改 `base_url` 即可
- Prompt 必须输出 JSON，带 Schema 校验
- 预留 OpenAI 降级路径

---

### Phase 2 — 主链路闭环

**Duration**: 依赖 Phase 1  
**Exit Criteria**: 首页 → 图谱页 端到端真实数据

| # | 任务 | 文件 | 复杂度 | 依赖 |
|---|------|------|--------|------|
| 2.1 | edges 字段映射 | `frontend/src/services/api.js` | 🟢 低 | 无 |
| 2.2 | plans.create 对接 | `frontend/src/services/api.js` | 🟡 中 | 传 `originalInput/targetNodeId` |
| 2.3 | AI 前端对接 | `frontend/src/services/api.js` | 🟢 低 | Phase 1 |
| 2.4 | 移除 plans Mock | `frontend/src/services/api.js` | 🟢 低 | 2.2 后 |
| 2.5 | 加载状态 + 取消按钮 | `frontend/src/pages/HomePage.jsx` | 🟢 低 | 2.3 后 |
| 2.6 | 拆分建议弹窗 | `frontend/src/pages/HomePage.jsx` | 🟡 中 | 2.1 后 |

**关键对齐**:
- 后端 edges: `{from_node, to_node}`
- 前端画布: `{from, to}`
- 映射层做双向转换

---

### Phase 3 — Mock 清零

**Duration**: 依赖 Phase 2  
**Exit Criteria**: 我的学习页全部真实数据

| # | 任务 | 文件 | 复杂度 |
|---|------|------|--------|
| 3.1 | notes 前端对接 | `frontend/src/services/api.js` | 🟢 低 |
| 3.2 | stats 前端对接 | `frontend/src/services/api.js` | 🟢 低 |
| 3.3 | plans archive/restore/delete | `frontend/src/services/api.js` | 🟢 低 |
| 3.4 | 清除 LocalStorage Mock | 多个文件 | 🟢 低 |
| 3.5 | 我的学习页完整 | `MyLearningPage.jsx` | 🟡 中 |

---

### Phase 4 — 补全 + 打磨

**Duration**: 依赖 Phase 3  
**Exit Criteria**: 推荐/调整功能 + 体验优化

| # | 任务 | 文件 | 复杂度 | 说明 |
|---|------|------|--------|------|
| 4.1 | recommend-next 后端 | `backend/routers/ai.py` | 🟡 中 | 可先规则引擎 |
| 4.2 | recommend-next 前端 | `GraphPage.jsx` | 🟢 低 | 推荐浮层 |
| 4.3 | clarify-goal 后端 | `backend/routers/ai.py` | 🟡 中 | 判断调整幅度 |
| 4.4 | clarify-goal 前端 | `GraphPage.jsx` | 🟡 中 | 调整确认弹窗 |
| 4.5 | apply-changes（可选） | `backend/routers/plans.py` | 🟡 中 | 改动大时需要 |
| 4.6 | Toast 错误提示 | `frontend/src/components/` | 🟢 低 | 全局错误 |
| 4.7 | 全局 Loading | `frontend/src/components/` | 🟢 低 | 异步反馈 |
| 4.8 | 回归测试 | 全链路 | 🟡 中 | 无回归 |

---

## 4. 依赖关系

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
   ↑           ↑           ↑
   │           │           │
   └─── 2.1/2.2/2.3 依赖 1.x 完成
               │
               └─── 3.x 依赖 2.x 完成
                           │
                           └─── 4.x 依赖 3.x 完成
```

---

## 5. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Phase 1 Prompt 调优困难 | 项目卡住 | 固定测试用例验证；准备 3 组基准输入 |
| Kimi 2.5 API 不稳定 | 生成失败 | 预留 OpenAI 降级路径 |
| 图谱生成质量差 | 体验差 | 设"最小节点数"阈值，低于则重试 |
| Phase 3 工作量低估 | 延期 | notes/stats 后端已完整，风险可控 |

---

## 6. 验收标准（Definition of Done）

### Phase 1 Done
- [ ] `POST /api/ai/parse-goal` 返回真实解析（非 Mock）
- [ ] `POST /api/ai/generate-graph` 返回真实图谱
- [ ] 错误时返回规范错误码

### Phase 2 Done
- [ ] 首页输入 → 确认弹窗 → 生成图谱 → 跳转图谱页
- [ ] 图谱显示真实节点和连线

### Phase 3 Done
- [ ] 我的学习页 4 个 Tab 全部真实数据
- [ ] 前端无 LocalStorage 业务数据

### Phase 4 Done
- [ ] 图谱页显示推荐下一步
- [ ] 可修改目标并预览变更
- [ ] 所有异步操作有 Loading + 错误提示

---

## 7. 附录

### A. 技术栈确认
- **LLM**: Kimi 2.5（月之暗面）
- **SDK**: OpenAI Python SDK（兼容模式）
- **Backend**: FastAPI + Pydantic + PostgreSQL
- **Frontend**: React 18 + Vite + Tailwind

### B. 参考文档
- PRD: `学习路径规划器 - MVP PRD（最终版）.md`
- 后端规范: `ConceptTree/spec/后端-通用规范.md`
- 前端架构: `ConceptTree/spec/前端-架构总览.md`
- AI 服务设计: `ConceptTree/spec/后端-AI服务.md`

---

*Document Version*: 1.0  
*Created*: 2025-03-17  
*Approved By*: [User]
