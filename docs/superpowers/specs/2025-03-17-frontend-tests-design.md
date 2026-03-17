# ConceptTree Frontend Tests Spec

> **Approved Date**: 2025-03-17  
> **Target**: 补充 Phase 2 前端重构的测试覆盖，包含纯数据转换的单元测试和主链路的 E2E 测试。

---

## 1. 目标与范围

在 Phase 2 的前端重构中，所有的 Mock 均被替换为了真实后端的 `fetchApi`。在此过程中，`api.js` 中新增了 `edges` 的双向字段映射（`from/to` ↔ `from_node/to_node`），且引入了处理 `shouldSplit` 的子目标拆分建议 UI。

**范围包含：**
- **单元测试 (Unit Tests)**：验证 `api.js` 中的纯函数（特别是容易丢属性的边缘映射函数）。
- **端到端测试 (E2E Tests)**：验证从用户输入到跳转图谱页的整个流程。

**范围不含：**
- **非独立 React 组件的单元测试**：因为 E2E 已经涵盖了绝大多数 DOM 和交互，单测只需覆盖非 UI 的纯逻辑部分，以保证 ROI。
- **需要真实后端的 E2E 测试**：E2E 层**必须使用 API 拦截 (Mock Request)** 隔离后端依赖，确保只验证前端行为（解耦数据库和 API Key 环境）。

---

## 2. 技术栈选择

- **单元测试**: `vitest` + `jsdom` (虽然测试纯函数，但加入 `jsdom` 可为将来组件单测铺路)。
- **端到端测试**: `@playwright/test`。

---

## 3. 测试用例清单

### 3.1 单元测试 (`api.test.js`)

**被测函数：**
`mapEdgesFromBackend(edges)` 与 `mapEdgesToBackend(edges)` (需确保从 `api.js` 导出，或者在测试文件中提取)。

**用例：**
1. `mapEdgesFromBackend`：输入有效后端结构 `[{ from_node: "A", to_node: "B", style: "dotted" }]`，输出应为 `[{ from: "A", to: "B", style: "dotted" }]`。
2. `mapEdgesFromBackend`：输入为 `null` 或 `undefined`，应返回 `[]`。
3. `mapEdgesToBackend`：输入有效前端结构 `[{ from: "C", to: "D", label: "x" }]`，输出应为 `[{ from_node: "C", to_node: "D", label: "x" }]`。
4. **防回滚用例**：如果输入对象既包含原名也包含新名，或是重复映射，应妥善处理（例如输入 `[{ from: "E", to: "F" }]` 传给 `mapEdgesFromBackend`，输出应原样保留 `{ from: "E", to: "F" }`，不会变成 undefined）。

### 3.2 E2E 测试 (`main-flow.spec.js`)

**被测链路：** HomePage 交互与 API 流程

**用例 1: Happy Path（标准图谱生成流程）**
1. 拦截 `/api/ai/parse-goal`，返回 { success: true, data: { interpretation: "学React", backgroundSummary: [], suggestedNodeCount: 5, shouldSplit: false } }。
2. 拦截 `/api/ai/generate-graph`，返回 Mock 的图谱 JSON。
3. 拦截 `/api/plans`，返回 { success: true, data: { id: "p123", title: "学React" } }。
4. 访问首页，输入 "我想学React"，点击生成。
5. 断言出现确认弹窗，内容包含 "学React"。
6. 点击 "确认生成"，断言页面变为加载态。
7. 断言 URL 发生跳转（包含 `p123`）。

**用例 2: Split Suggestions（目标过大拆分建议流程）**
1. 拦截 `/api/ai/parse-goal`，返回 { success: true, data: { interpretation: "目标太大", shouldSplit: true, splitSuggestions: [{title: "小目标A", description: "desc"}] } }。
2. 访问首页，输入宽泛目标，点击生成。
3. 断言弹窗中出现了 "小目标A" 的可点击卡片。
4. 点击该卡片。
5. 断言弹窗关闭，且输入框的值被替换为 "小目标A"。

**用例 3: MyLearning Stats 展示**
1. 拦截 `/api/stats/overview` 和 `/api/stats/distribution`，返回包含固定数值（如 completedPlans: 42）的 JSON。
2. 拦截 `/api/user/profile` 和 `/api/plans` (规避报错)。
3. 在认证上下文中 Mock 登录态（或拦截相关 API 设置 localstorage）。
4. 导航到 `/my-learning`。
**用例 4: 异常处理 (Error State)**
1. 拦截 `/api/ai/parse-goal`，强制返回 500 错误 `{ success: false, error: { message: "AI Service Error" } }`。
2. 访问首页，输入目标，点击生成。
3. 断言页面恢复到可交互状态，且控制台或 UI 层面合理捕获了错误（目前 UI 尚未做 Toast，但不能白屏死锁）。

**用例 5: 空状态展示 (Empty State)**
1. 拦截 `/api/stats/overview` 和 `/api/stats/distribution`，返回空数据或 0。
2. 导航到 `/my-learning` 统计 Tab。
3. 断言页面渲染出了空状态提示文案（"开始学习后，这里将显示你的知识领域分布"）。