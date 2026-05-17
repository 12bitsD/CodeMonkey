# Harness Plan Management Upgrade

## 目标

把现有“图谱生成 + 归档状态”升级成真正的学习计划系统，让用户可以：

- 将生成的图谱直接视为学习计划
- 为计划设置学习周期、预计完成时间和提醒方式
- 在首页和“我的学习”里持续跟踪计划状态
- 区分“已完成归档”“手动归档”“暂停中”等不同计划状态

这次升级以 Harness Engineering 为核心，优先保证：

- 在现有 `plans` 主线之上增量演进
- 前后端数据结构一致
- 先做站内计划管理与提醒，再考虑外部提醒
- 每个阶段都能单独验收，不阻塞当前图谱主流程

---

## 现状判断

当前项目已经具备“计划系统雏形”：

- 后端 `plans` 已有 `status / progress / total / last_access_at`
- 前端已有 `archivePlan / restorePlan / updatePlanProgress`
- 首页已展示活动计划和进度条
- “我的学习”已有“归档计划”标签页
- 节点完成后后端已支持自动归档

当前缺口主要在：

- `plan` 还只是“图谱容器”，不是“可运营的学习计划”
- 没有学习周期、截止时间、提醒、暂停等字段
- 归档只有单一状态，缺少“完成归档 / 手动归档 / 暂停”语义
- 首页没有“今天该学什么 / 本周计划进度”这一层

---

## 产品原则

### 1. 图谱即计划

不额外新建一套“学习计划”对象，直接在现有 `plans` 上扩展元数据。

这样可以避免：

- 图谱和计划双轨维护
- 同一学习任务拆成两套数据源
- 前端上下文和 API 成本翻倍

### 2. 先做站内管理，后做外部提醒

第一版提醒只做站内提醒与计划看板，不直接接邮件、短信或系统推送。

原因：

- 当前项目还没有稳定调度器
- 站内提醒更容易验证真实使用价值
- 可以先跑通节奏感和留存逻辑

### 3. 状态语义清晰

计划状态建议从现在的：

- `active`
- `archived`

扩展为：

- `active`：正常学习中
- `paused`：计划暂停
- `completed`：学习完成
- `archived`：手动归档或历史收纳

如果不想第一版直接改枚举过多，也可以保守落地为：

- `active`
- `paused`
- `archived`

并增加 `archived_reason = completed | manual`

---

## Sprint 拆分

## Sprint A — 计划元数据打底

### 目标

让 `plans` 从“图谱记录”升级成“可管理的学习计划”。

### 后端

扩展 `plans` 表字段：

- `start_date`
- `target_end_date`
- `study_frequency`
- `study_days_per_week`
- `reminder_enabled`
- `reminder_time`
- `reminder_timezone`
- `status`
- `archived_reason`

建议字段定义：

```sql
ALTER TABLE plans ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS target_end_date TIMESTAMPTZ;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS study_frequency TEXT DEFAULT 'flexible';
ALTER TABLE plans ADD COLUMN IF NOT EXISTS study_days_per_week INTEGER DEFAULT 3;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_time TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS reminder_timezone TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS archived_reason TEXT;
```

扩展 API：

- `GET /api/plans`
  返回完整计划元数据
- `PUT /api/plans/{id}`
  支持更新学习周期、截止时间、提醒开关等
- `PUT /api/plans/{id}/archive`
  支持可选 `reason`
- `PUT /api/plans/{id}/pause`
- `PUT /api/plans/{id}/resume`

### 前端

扩展 `PlanContext` 类型与默认值：

- `studyFrequency`
- `studyDaysPerWeek`
- `targetEndDate`
- `reminderEnabled`
- `reminderTime`
- `reminderTimezone`
- `archivedReason`

在图谱页增加“计划设置”入口：

- 学习周期
- 每周学习天数
- 预计完成时间
- 是否提醒

### 验收

- 现有计划读取不报错
- 老计划没有新字段时也能正常显示
- 用户能编辑计划节奏并持久化

---

## Sprint B — 首页与“我的学习”计划化

### 目标

让用户能明显感受到“这是学习计划”，而不是只有一张图谱。

### 首页升级

每个活动计划卡片补充：

- 计划状态
- 学习频率
- 预计完成日期
- 今日建议学习节点
- 是否已开启提醒

增加一个“今日学习”模块：

- 今天建议学习哪一个计划
- 该计划下推荐学习哪个节点
- 最近一次学习时间

### 我的学习升级

将当前“归档计划”页签拆出更清晰的分类：

- 进行中
- 已暂停
- 已完成
- 已归档

或者保持单页签，但支持状态过滤。

每个计划卡片增加：

- 计划周期
- 完成率
- 最近学习时间
- 归档原因

### 图谱页升级

图谱页顶部补充计划信息条：

- 开始日期
- 目标日期
- 学习频率
- 当前进度
- 今日建议

### 验收

- 首页可以看懂“计划节奏”
- 归档不再只是“消失”，而是进入明确的状态分类
- 图谱页和首页展示的计划信息一致

---

## Sprint C — 站内提醒 MVP

### 目标

不做复杂通知系统，先做站内提醒闭环。

### 功能范围

新增“提醒计算”逻辑：

- 根据 `study_frequency`
- `study_days_per_week`
- `last_access_at`
- `progress / total`

计算：

- 今天是否该学习
- 已拖延几天
- 下次建议学习时间

首页提醒表现：

- “今天该继续学习 Transformer 架构”
- “你已经 3 天没有继续这个计划”
- “本周目标 3 次，当前已完成 1 次”

### 技术实现

第一版不建消息表也可以，直接由后端动态计算提醒文案。

如果要持久化提醒事件，可以新增表：

- `plan_reminders`

但建议第二阶段再做。

### 验收

- 用户打开首页时能看到明确的计划提醒
- 暂停计划不会继续提醒
- 已完成计划不会进入“今日待学”

---

## Sprint D — 自动排程与计划推荐

### 目标

让 AI 推荐节点和计划周期打通，而不是只看图结构。

### 改动

在 `recommend-next` 逻辑中引入计划元数据：

- 计划状态
- 截止日期
- 本周学习频率
- 最近学习时间

推荐时输出：

- 推荐节点
- 推荐理由
- 推荐紧急度
- 是否属于“今日必学”

### 前端

首页卡片和图谱页都展示：

- 今日推荐
- 推荐理由
- 紧急程度标签

### 验收

- 推荐节点不再只是“下一个没学的节点”
- 计划节奏会影响推荐顺序

---

## 数据模型建议

### `plans` 新字段建议

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `start_date` | `TIMESTAMPTZ` | 计划开始时间 |
| `target_end_date` | `TIMESTAMPTZ` | 计划目标完成时间 |
| `study_frequency` | `TEXT` | `flexible / daily / weekly / custom` |
| `study_days_per_week` | `INTEGER` | 每周目标学习次数 |
| `reminder_enabled` | `BOOLEAN` | 是否开启提醒 |
| `reminder_time` | `TEXT` | 提醒时间，如 `21:00` |
| `reminder_timezone` | `TEXT` | 时区 |
| `archived_reason` | `TEXT` | `completed / manual` |

### 前端 plan 类型扩展

在 `frontend/src/types/index.js` 中补齐这些字段，保持 `createEmptyPlan()` 与后端一致。

---

## API 设计建议

### 1. 计划设置更新

`PUT /api/plans/{id}`

请求体允许：

```json
{
  "title": "Transformer 学习计划",
  "startDate": "2026-04-18T00:00:00Z",
  "targetEndDate": "2026-05-18T00:00:00Z",
  "studyFrequency": "weekly",
  "studyDaysPerWeek": 4,
  "reminderEnabled": true,
  "reminderTime": "21:00",
  "reminderTimezone": "Asia/Shanghai"
}
```

### 2. 暂停 / 恢复

- `PUT /api/plans/{id}/pause`
- `PUT /api/plans/{id}/resume`

### 3. 归档原因

`PUT /api/plans/{id}/archive`

```json
{
  "reason": "manual"
}
```

自动学完归档时后端写：

```json
{
  "reason": "completed"
}
```

### 4. 今日学习推荐

可新增：

`GET /api/plans/recommendation/today`

返回：

- 计划 id
- 推荐节点 id
- 推荐理由
- 紧急度

---

## 前端落点建议

### HomePage

新增：

- 今日学习卡片
- 计划节奏标签
- 截止时间提示
- 暂停 / 恢复操作

### GraphPage

新增：

- “计划设置”按钮
- 计划元信息面板
- 当前计划节奏与目标显示

### MyLearningPage

增强：

- 状态筛选
- 计划属性展示
- 快速恢复 / 继续学习

---

## Harness 守门点

### 1. 兼容老数据

必须保证历史 `plans` 记录没有新字段时也能正常读写。

### 2. 不打断图谱主流程

生成图谱、学习节点、保存笔记这些已有主流程不能因为计划元数据缺失而报错。

### 3. 状态机单一来源

不要让前端自行推断“已完成”与“已归档”，由后端统一给出。

### 4. 提醒先动态计算

第一版提醒不直接引入定时任务和消息队列，避免范围失控。

---

## 测试计划

### 后端测试

新增建议：

- `backend/tests/test_plan_management_api.py`
- `backend/tests/test_plan_status_transitions.py`
- `backend/tests/test_today_plan_recommendation.py`

覆盖：

- 更新学习周期字段
- 暂停 / 恢复计划
- 自动归档与归档原因
- 今日提醒逻辑

### 前端测试

新增建议：

- `frontend/src/pages/HomePage.plan-management.test.jsx`
- `frontend/src/pages/MyLearningPage.plan-status.test.jsx`
- `frontend/src/contexts/PlanContext.plan-settings.test.jsx`

覆盖：

- 计划元数据展示
- 状态切换
- 提醒卡片显示
- 设置保存与回显

### 测试脚本

建议新增：

- `scripts/test_plan_management.ps1`

执行：

- 后端 pytest
- 前端 vitest
- 相关 eslint

---

## 推荐实施顺序

1. `Sprint A`
先扩展 `plans` 数据模型和 API

2. `Sprint B`
把首页 / 我的学习 / 图谱页展示打通

3. `Sprint C`
做站内提醒

4. `Sprint D`
让 AI 推荐与学习周期联动

---

## 验收标准

- 用户生成图谱后，可以直接把它当作学习计划持续管理
- 计划不再只有“归档 / 非归档”，而是有明确的生命周期状态
- 用户可以设置学习节奏与完成目标
- 首页可以看到“今天该学什么”
- 归档页能体现计划历史，而不是空壳列表

---

## 结论

这次升级最关键的不是“再加一个归档页面”，而是把现有 `plans` 从图谱容器升级成学习管理中枢。

一旦这条线打通，你现在已经有的：

- 图谱生成
- AI 推荐节点
- 笔记系统
- 归档系统

就会自然收敛成一个完整的“学习路径规划 + 执行 + 跟踪”闭环。
