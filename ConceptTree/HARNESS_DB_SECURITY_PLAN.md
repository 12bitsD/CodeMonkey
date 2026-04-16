# ConceptTree Database Security Plan

> Focus: 以 Harness Engineering 为核心，修复 Supabase `rls_disabled_in_public` 类数据库暴露风险，并把后续回归检查自动化。
> Date: 2026-04-16

---

## 1. 问题定义

当前告警表明：至少有一个处于 `public` schema 的表未启用 Row-Level Security。

这类问题的真实风险不是“代码里有一个小 bug”，而是：

1. 任何拿到项目 URL 与公开 key 的人，都可能通过 Supabase Data API 直接访问表。
2. 一旦没有 RLS，读、写、删都会落到“默认放行”或“权限过宽”的危险状态。
3. 即使我们的主业务流量走自建后端，未加固的 Supabase public surface 依然是独立攻击面。

从当前仓库状态看：

1. [backend/schema.sql](/abs/path/c:/Users/Victor/Desktop/CodeMonkey666/CodeMonkey/ConceptTree/backend/schema.sql) 已定义核心表，但没有任何 `ENABLE ROW LEVEL SECURITY`、`FORCE ROW LEVEL SECURITY`、`CREATE POLICY`。
2. [HARNESS_PLAN.md](/abs/path/c:/Users/Victor/Desktop/CodeMonkey666/CodeMonkey/ConceptTree/HARNESS_PLAN.md) 已有 hooks 思路，但还没有覆盖 Supabase RLS 漏洞场景。

---

## 2. 目标

本轮更新要同时完成三件事：

1. 立刻封堵 public schema 的未授权访问面。
2. 让数据库安全规则进入版本控制，而不是停留在 Dashboard 手工修复。
3. 把 RLS / grant / policy 检查接入 Harness，防止以后再回退。

---

## 3. 执行原则

1. 默认拒绝：没有显式 policy 的访问一律不允许。
2. 服务端优先：现阶段业务继续以自建 backend 访问数据库为主，不依赖前端直连 Supabase 表。
3. 版本化修复：所有 RLS、policy、grant 变更都必须落到 SQL 文件。
4. Harness 守门：数据库安全不能靠“记得做”，而要靠 hook 和脚本持续检查。

---

## 4. 修复范围

建议把以下表全部纳入 RLS 整治范围：

1. `users`
2. `user_profiles`
3. `plans`
4. `nodes`
5. `edges`
6. `learning_sessions`
7. `notes`

其中：

1. `plans / notes / learning_sessions / user_profiles` 属于明确的用户私有数据。
2. `nodes / edges` 虽然从业务上挂在 `plan` 下，但同样会泄露个人学习图谱，应跟随 `plans` 所有权保护。
3. `users` 至少不应被 `anon` 或宽松 `authenticated` 直接扫表。

---

## 5. Sprint Plan

### Sprint A: 紧急止血

目标：先把 “公开可读写” 变成 “默认不可访问”。

代码与平台动作：

1. 新增 SQL 修复文件，建议路径：
   `backend/sql/2026-04-16_enable_rls.sql`
2. 对上述全部表执行：
   `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
3. 对高风险私有表执行：
   `ALTER TABLE ... FORCE ROW LEVEL SECURITY;`
4. 审核并收紧 `anon` / `authenticated` 的表级 grant。
5. 如果前端当前并未直接使用 Supabase Data API，则第一版可以先不开放任何 public policy，直接让 public API 全部被 RLS 拦下。

交付标准：

1. Supabase 安全告警不再出现 `rls_disabled_in_public`
2. 未登录用户通过 public API 无法直接读取业务表

### Sprint B: 最小可用策略

目标：把“禁止一切”升级为“只允许正确主体访问自己的数据”。

代码任务：

1. 若未来要支持 Supabase Auth 直连，补齐 `CREATE POLICY`。
2. `plans / notes / learning_sessions / user_profiles` 使用 owner-based policy。
3. `nodes / edges` 使用 join-based policy，通过所属 `plan.user_id` 约束访问。
4. 明确区分：
   `anon` 无权访问
   `authenticated` 仅能访问自身数据
   `service_role` / backend 走受信任通道

注意：

1. 如果当前项目并未接入 Supabase Auth，而是自定义 JWT + 直连 Postgres，那么 policy 设计要避免“写了看起来很安全、实际没有任何主体能命中”的伪安全。
2. 这类情况下，短期可以选择：
   完全禁止 public API
   后续如果接 Supabase Auth，再补用户级 policy

### Sprint C: Harness 常态化守门

目标：以后有人改 schema、grant、database 逻辑时，系统自动提醒或阻断。

---

## 6. Harness 设计

### Hook A: PreToolUse 阻止危险 SQL 回退

触发条件：

1. 编辑 `.sql`
2. 编辑 `backend/schema.sql`
3. 编辑数据库迁移目录

行为：

1. 如果检测到 `DISABLE ROW LEVEL SECURITY`
2. 或检测到对 `anon` / `authenticated` 的宽泛 `GRANT ALL`
3. 或删除已有 `FORCE ROW LEVEL SECURITY`

则直接阻断，并提示：

`数据库安全基线禁止关闭 RLS 或向 public role 放宽表权限，请先更新安全计划与测试。`

### Hook B: PostToolUse 数据库安全静态扫描

触发文件：

1. `backend/schema.sql`
2. `backend/sql/*.sql`
3. `backend/database.py`

检查点：

1. 目标表是否存在 `ENABLE ROW LEVEL SECURITY`
2. 高敏表是否存在 `FORCE ROW LEVEL SECURITY`
3. 是否出现可疑 grant：
   `GRANT ALL ON`
   `TO anon`
   `TO public`
4. `database.py` 是否重新引入字符串拼接 SQL 风险

建议命令风格：

1. `rg "ENABLE ROW LEVEL SECURITY|FORCE ROW LEVEL SECURITY|GRANT .* TO anon|GRANT .* TO public" backend`
2. 对 schema 文件做白名单断言，而不是只做关键字存在检查

### Hook C: PostToolUse 自动跑数据库安全测试

触发条件：

1. 修改任何 `.sql`
2. 修改 `backend/database.py`
3. 修改认证相关文件

自动执行：

1. `python -m pytest tests/test_db_security_rls.py -q`
2. 必要时附加：
   `python -m pytest tests/test_sprint1_security.py -q`

### Hook D: UserPromptSubmit 风险提醒

当用户请求包含以下意图时输出提醒：

1. “先把 RLS 关掉”
2. “直接开放 public 读写”
3. “让前端直接拿 anon key 查全表”

提醒内容：

`这会重新暴露 Supabase public attack surface。请优先走 backend proxy 或显式 owner policy。`

### Scheduled Job: 每周数据库安全基线巡检

建议时间：

1. 每周一 10:00

巡检内容：

1. 核对所有核心表是否启用 RLS
2. 核对是否存在 `anon/public` 宽泛 grant
3. 核对测试脚本是否仍通过
4. 输出一份简短状态报告，对比本计划完成度

---

## 7. 代码落地建议

### 7.1 SQL 层

新增文件：

1. `backend/sql/2026-04-16_enable_rls.sql`

建议内容分层：

1. `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
2. `ALTER TABLE ... FORCE ROW LEVEL SECURITY`
3. 清理宽泛 grant
4. 按需创建 policy
5. 为 `nodes / edges` 写基于 `plans` 的 owner join policy

### 7.2 Schema 基线

更新：

1. [backend/schema.sql](/abs/path/c:/Users/Victor/Desktop/CodeMonkey666/CodeMonkey/ConceptTree/backend/schema.sql)

要求：

1. 新环境初始化时就自带 RLS
2. 不依赖“上线后手动点 Dashboard”

### 7.3 文档

更新：

1. `HARNESS_PLAN.md`
2. 可选新增：
   `ACCEPTANCE_PLAN.md` 中的数据库安全验收项

文档需要回答：

1. 哪些表必须启用 RLS
2. 为什么当前阶段 public API 默认不开放
3. 以后若接 Supabase Auth，policy 应如何演进

---

## 8. 测试方案

建议新增测试文件：

1. `backend/tests/test_db_security_rls.py`

测试应覆盖：

1. 核心表列表全部存在 RLS 语句
2. 高敏表列表全部存在 `FORCE ROW LEVEL SECURITY`
3. schema 或 migration 中不存在危险 grant
4. 若有 policy，校验 policy 名称与目标表对应完整

建议新增脚本：

1. `scripts/test_db_security.ps1`

脚本内容建议：

1. 跑 `pytest tests/test_db_security_rls.py -q`
2. 跑与 auth / security 相关的补充测试
3. 输出通过/失败摘要

---

## 9. 验收标准

本轮完成的验收线：

1. Supabase 后台不再报告 `rls_disabled_in_public`
2. 所有核心业务表都启用 RLS
3. 高敏表强制 RLS
4. 没有对 `anon/public` 的危险 grant
5. 数据库安全测试脚本能稳定通过
6. Harness hooks 已覆盖 SQL 回退与 grant 放宽场景

---

## 10. 推荐实施顺序

1. 先确认 Supabase 后台具体报错的表名
2. 先写 SQL 止血脚本，启用 RLS 并收紧 grant
3. 再把规则合并回 `backend/schema.sql`
4. 再补 `pytest` 与 `PowerShell` 测试脚本
5. 最后把 hooks 写进 Harness 配置，形成长期守门

---

## 11. 决策建议

基于当前代码库，我建议采用这条路线：

1. 短期：public API 默认全关，backend 继续作为唯一受信入口
2. 中期：把 RLS 与 grant 全部版本化
3. 长期：如果要做前端直连 Supabase，再基于 Supabase Auth 补 owner policy，而不是现在为了“方便”先开口子

这样最符合 Harness Engineering 的核心思想：

1. 先把高风险入口关掉
2. 再把正确做法写成自动化约束
3. 最后让团队以后不需要靠记忆重复修同一类问题
