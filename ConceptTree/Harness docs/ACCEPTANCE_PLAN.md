# ConceptTree — 验收方案

> 版本：1.0  
> 日期：2026-04-14  
> 范围：Sprint 0 ~ Sprint 3 全部已交付功能  
> 环境：本地开发环境（后端 http://localhost:8000，前端 http://localhost:3000）

---

## 一、验收总览

| Sprint | 核心功能 | 自动化测试 | 手动验收 |
|--------|---------|-----------|---------|
| Sprint 0 | 安全修复（SQL 注入、JWT 配置） | — | ✅ 需手动验 |
| Sprint 1 | 安全加固（CORS、限流、密码、注销） | — | ✅ 需手动验 |
| Sprint 2 | F1 学习目的、F3 阶段分组、F5 SSE 流式 | 后端 36 项 + 前端 15 项 | ✅ 需手动验 |
| Sprint 3 | F2/F7 AI 内容展开、F4 聊天助手、F6 缓存 | 后端 31 项 + 前端 16 项 | ✅ 需手动验 |

**验收通过标准：**
- 所有自动化测试 100% 通过
- 所有手动用例执行结果符合预期（无 FAIL 项）
- 关键路径（注册→建图→学习→聊天）端到端无报错

---

## 二、环境准备

### 2.1 启动服务

```bash
# 后端（终端 1）
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 前端（终端 2）
cd frontend
npx vite --port 3000
```

### 2.2 运行自动化测试

```bash
# 后端 Sprint 2 测试（约 2 分钟）
cd backend
python -m pytest tests/test_sprint2_features.py -v

# 后端 Sprint 3 测试（约 5 分钟，含 LLM 真实调用）
python -m pytest tests/test_sprint3_features.py -v

# 前端 Sprint 2 测试
cd frontend
npx vitest run src/services/api.sprint2.test.js --reporter=verbose

# 前端 Sprint 3 测试
npx vitest run src/services/api.sprint3.test.js --reporter=verbose
```

### 2.3 测试账号

在 http://localhost:3000 注册测试账号，或使用已有账号。

---

## 三、Sprint 0 验收 — 安全基础修复

### TC-S0-01：数据库 Schema 注入防护

**前置条件：** 后端已启动  
**测试步骤：**
1. 打开 `backend/database.py`，检查 `_connect()` 函数
2. 确认 schema 名通过正则白名单验证（`^[a-z_][a-z0-9_]{0,62}$`）
3. 尝试传入非法 schema 名触发异常

```python
# 验证命令
python -c "
from database import _VALID_SCHEMA_RE
tests = ['public', 'test_schema', '1invalid', 'drop; --']
for t in tests:
    print(t, bool(_VALID_SCHEMA_RE.match(t)))
"
```

**预期结果：**
- `public` → True
- `test_schema` → True
- `1invalid` → False
- `drop; --` → False

**判定：** ✅ PASS / ❌ FAIL

---

### TC-S0-02：JWT 配置来源验证

**测试步骤：**
1. 打开 `backend/utils/auth.py`
2. 确认 `SECRET_KEY` 和过期时间来自 `config.py`，非硬编码

```bash
grep -n "SECRET_KEY\|EXPIRE" backend/utils/auth.py
```

**预期结果：** 引用 `settings.JWT_SECRET_KEY` 和 `settings.JWT_EXPIRE_DAYS`，不包含 `= "secret"` 等硬编码字符串

**判定：** ✅ PASS / ❌ FAIL

---

## 四、Sprint 1 验收 — 安全加固

### TC-S1-01：登录频率限制

**前置条件：** 后端已启动，slowapi 已配置  
**测试步骤：**
1. 使用错误密码连续登录 6 次以上

```bash
for i in 1 2 3 4 5 6; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrongpw"}'
done
```

**预期结果：** 前几次返回 `401`，超限后返回 `429 Too Many Requests`

**判定：** ✅ PASS / ❌ FAIL

---

### TC-S1-02：密码强度验证

**测试步骤：**
1. 尝试注册弱密码账号

```bash
# 短密码
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"weak@test.com","password":"123"}'
```

**预期结果：** 返回 `400`，提示密码不符合要求（需 8 位以上）

**判定：** ✅ PASS / ❌ FAIL

---

### TC-S1-03：注销使 Token 失效（黑名单）

**测试步骤：**
1. 登录获取 Token
2. 调用 `/api/auth/logout` 注销
3. 使用同一 Token 访问受保护接口

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"yourpw"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 2. 注销
curl -s -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"

# 3. 再次访问
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/user/profile \
  -H "Authorization: Bearer $TOKEN"
```

**预期结果：** 步骤 3 返回 `401 Unauthorized`

**判定：** ✅ PASS / ❌ FAIL

---

### TC-S1-04：异常不泄露内部信息

**测试步骤：**
1. 发送格式错误的请求，检查响应体

```bash
curl -s -X POST http://localhost:8000/api/plans \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalidtoken" \
  -d '{"bad": "data"}'
```

**预期结果：** 响应中不包含 Python traceback、文件路径、堆栈信息，只有标准 `{"success": false, "error": {...}}` 结构

**判定：** ✅ PASS / ❌ FAIL

---

## 五、Sprint 2 验收 — 核心学习体验

### TC-F1-01：创建计划时选择学习目的

**测试步骤：**
1. 打开 http://localhost:3000，登录
2. 在首页输入学习目标（如：`学习 React Hooks`），点击生成
3. 在弹出的确认弹窗中，观察是否有学习目的选择器

**预期结果：**
- 确认弹窗中有三个选项：`了解这个领域`、`项目/工作中能用`、`系统精通`
- 默认选中 `项目/工作中能用`
- 三个按钮有不同的视觉状态（选中高亮）

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F1-02：学习目的影响节点数量和深度

**测试步骤：**
1. 分别用 `了解这个领域` 和 `系统精通` 各生成一张图谱（主题相同）
2. 对比两张图谱的节点数量

**预期结果：**
- `了解` 模式：节点数约 5-7 个
- `系统精通` 模式：节点数约 10-15 个，且含「进阶」阶段

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F3-01：图谱显示阶段背景区域

**测试步骤：**
1. 打开任意一张学习图谱
2. 观察画布是否有彩色背景区域标注

**预期结果：**
- 存在半透明彩色背景块，将节点按阶段分组
- 每个区域左上角有阶段标签（`地基` / `核心` / `应用` / `进阶`）
- 颜色区分：地基-紫色、核心-青色、应用-蓝色、进阶-橙色

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F3-02：节点包含阶段数据

**测试步骤：**
1. 创建一张新图谱后，通过 API 检查节点数据

```bash
curl -s http://localhost:8000/api/plans/{PLAN_ID}/graph \
  -H "Authorization: Bearer $TOKEN" | \
  python -c "import sys,json; nodes=json.load(sys.stdin)['data']['nodes']; [print(n['name'], n.get('phase'), n.get('phase_order')) for n in nodes]"
```

**预期结果：** 每个节点有 `phase`（非空）、`phase_order`（1-4）、`depth_level` 字段

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F5-01：图谱生成 SSE 流式渲染

**测试步骤：**
1. 在首页输入新目标，选学习目的后点击确认
2. 观察图谱生成过程中，节点是否逐个出现

**预期结果：**
- 加载阶段显示 `生成节点 N/M` 的进度提示
- 节点在流式传输过程中逐步出现在画布上（非一次性全部出现）
- 所有节点到达后，进度提示消失，图谱可正常交互

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F5-02：后端 generate-graph 接口返回 SSE

```bash
curl -N -s -X POST http://localhost:8000/api/ai/generate-graph \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"input":"React Hooks","interpretation":"学习 React Hooks","learning_purpose":"apply"}' \
  | head -5
```

**预期结果：** 每行格式为 `data: {"type": "meta/node/edges/done", ...}`

**判定：** ✅ PASS / ❌ FAIL

---

## 六、Sprint 3 验收 — AI 深度内容 + 聊天助手

### TC-F7-01：核心内容条目可点击展开 AI 解释

**测试步骤：**
1. 打开任意图谱，点击一个节点，打开节点详情面板
2. 找到「核心内容」区域
3. 点击其中任意一条内容

**预期结果：**
- 每条内容旁有一个 Sparkles ✨ 图标，悬停变色
- 点击后出现「AI 正在生成解释...」加载占位
- 解释文字流式出现在该条目下方（无需等待全部完成）
- 展开后图标变为 ▼，再次点击可折叠

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F7-02：AI 解释缓存（同一条目不重复调用 LLM）

**测试步骤：**
1. 对某节点的某条内容点击展开，等待 AI 解释生成完成
2. 折叠后再次点击同一条目

**预期结果：**
- 第二次点击**立即**展开内容，无「AI 正在生成…」过程
- 响应时间 < 100ms（从本地状态读取，不再调用 LLM）

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F7-03：不同节点的解释互不干扰

**测试步骤：**
1. 展开节点 A 的第 1 条解释
2. 切换到节点 B，展开其第 1 条解释
3. 切换回节点 A

**预期结果：** 节点 A 的解释内容仍正确显示，与节点 B 内容无混淆

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F4-01：浮动聊天按钮仅在节点选中时出现

**测试步骤：**
1. 打开图谱页面，不选中任何节点
2. 检查左下角是否有聊天按钮
3. 点击一个节点，再次检查

**预期结果：**
- 未选中节点时：左下角无聊天按钮
- 选中节点后：左下角出现 💬 聊天按钮

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F4-02：聊天面板打开与关闭

**测试步骤：**
1. 选中一个节点
2. 点击聊天按钮
3. 再次点击关闭

**预期结果：**
- 点击后面板从左下角弹出，显示当前节点名称
- 面板内有消息区域 + 输入框 + 发送按钮
- 再次点击按钮（变为 × ）后面板收起

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F4-03：聊天流式回复

**测试步骤：**
1. 打开聊天面板，输入问题（如：`这个概念最难理解的部分是什么？`）
2. 按 Enter 或点击发送

**预期结果：**
- 用户消息立即出现在气泡中
- AI 回复气泡出现，文字流式输出（逐字/逐词）
- 回复完成后发送按钮恢复可用
- 输入框自动清空

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F4-04：聊天上下文与节点绑定

**测试步骤：**
1. 在节点 A 聊天，询问一个问题
2. 切换到节点 B，观察聊天面板

**预期结果：**
- 切换节点后，聊天记录自动清空（新节点新会话）
- 面板标题更新为节点 B 的名称

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F4-05：多轮对话连贯性

**测试步骤：**
1. 连续发送 3 条消息，形成多轮对话
2. 观察 AI 回答是否考虑了上下文

**预期结果：** AI 回复引用/延续之前对话内容，不是孤立回答

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F6-01：LLM 分级调用验证

**测试步骤：**  
检查后端配置文件中不同任务使用的模型

```bash
python -c "
import json
configs = ['explain_topic', 'chat', 'generate_graph']
for c in configs:
    with open(f'backend/services/llm/configs/{c}.json') as f:
        d = json.load(f)
        print(c, '->', d.get('model_params', {}).get('model', '(inherits default)'))
"
```

**预期结果：**
- `generate_graph` → `moonshot-v1-32k`（复杂任务用大模型）
- `explain_topic` → `moonshot-v1-8k`（轻量任务用小模型）
- `chat` → `moonshot-v1-8k`（轻量任务用小模型）

**判定：** ✅ PASS / ❌ FAIL

---

### TC-F6-02：content_cache 字段持久化

**测试步骤：**
1. 展开某节点的某条 AI 解释（首次生成）
2. 刷新页面，再次打开该节点
3. 再次点击同一条目

**预期结果：** 刷新后再次点击无 loading 过程，内容立即显示（从 DB 缓存读取）

> 注：此测试验证 DB 持久化，与 TC-F7-02 的内存缓存不同。

**判定：** ✅ PASS / ❌ FAIL

---

## 七、端到端关键路径验收

### E2E-01：完整学习流程（黄金路径）

**步骤：**

| # | 操作 | 预期结果 |
|---|------|---------|
| 1 | 访问 http://localhost:3000 | 页面正常加载，显示登录/注册 |
| 2 | 注册新账号（邮箱+密码≥8位） | 注册成功，自动跳转首页 |
| 3 | 输入学习目标：`学习 Python 装饰器` | 解析完成，弹出确认弹窗 |
| 4 | 选择学习目的：`项目/工作中能用` | 选中状态高亮 |
| 5 | 点击「开始生成」 | 显示进度条，节点逐个出现 |
| 6 | 图谱生成完成 | 有阶段背景区域，节点 7-10 个 |
| 7 | 点击一个节点 | 右侧面板展开，显示节点详情 |
| 8 | 点击核心内容中的一条 | AI 解释流式输出 |
| 9 | 点击聊天按钮，提问 | AI 流式回复 |
| 10 | 双击节点标记已学 | 节点变深色，进度条更新 |
| 11 | 点击返回首页 | 图谱进度保存，首页列表中可见 |

**判定：** 所有步骤均符合预期 → ✅ PASS，任一步骤失败 → ❌ FAIL

---

### E2E-02：错误恢复路径

| # | 操作 | 预期结果 |
|---|------|---------|
| 1 | 未登录直接访问 `/graph/xxx` | 重定向到登录页 |
| 2 | 登录后访问不存在的计划 ID | 显示「未找到学习计划」提示，有返回按钮 |
| 3 | 聊天时断网 | 显示「回复失败，请重试」，不崩溃 |

**判定：** ✅ PASS / ❌ FAIL

---

## 八、自动化测试验收汇总

执行以下命令获取最终数字：

```bash
# 后端
cd backend
python -m pytest tests/test_sprint2_features.py tests/test_sprint3_features.py -v --tb=short 2>&1 | tail -5

# 前端
cd frontend
npx vitest run src/services/api.sprint2.test.js src/services/api.sprint3.test.js 2>&1 | tail -5
```

| 套件 | 测试数 | 目标 |
|------|--------|------|
| `test_sprint2_features.py` | 36 | 36/36 ✅ |
| `test_sprint3_features.py` | 31 | 31/31 ✅ |
| `api.sprint2.test.js` | 15 | 15/15 ✅ |
| `api.sprint3.test.js` | 16 | 16/16 ✅ |
| **合计** | **98** | **98/98** |

---

## 九、已知限制 / 本次不验收项

| 项目 | 原因 | 计划 Sprint |
|------|------|------------|
| 「保存 AI 回复为笔记」按钮 | Sprint 3 未完成此子功能 | Sprint 3 补充 |
| S11 Docker 非 root 用户 | 仅本地开发，无 Docker 验收场景 | Sprint 4 |
| S13 安全响应头中间件 | Sprint 4 范围 | Sprint 4 |
| S14 审计日志 | Sprint 4 范围 | Sprint 4 |
| 连接池（psycopg2.pool） | Sprint 4 范围 | Sprint 4 |
| Context 拆分 | Sprint 4 范围 | Sprint 4 |
| 50+ 节点图谱性能 | 当前用例节点数 < 20 | Sprint 4 |

---

## 十、验收签核

| 验收项 | 负责人 | 结果 | 备注 |
|--------|--------|------|------|
| 自动化测试 98/98 通过 | | ⬜ | |
| TC-S0 安全修复 2 项 | | ⬜ | |
| TC-S1 安全加固 4 项 | | ⬜ | |
| TC-F1 学习目的 2 项 | | ⬜ | |
| TC-F3 阶段分组 2 项 | | ⬜ | |
| TC-F5 流式渲染 2 项 | | ⬜ | |
| TC-F7 AI 解释 3 项 | | ⬜ | |
| TC-F4 聊天助手 5 项 | | ⬜ | |
| TC-F6 LLM 分级 2 项 | | ⬜ | |
| E2E 关键路径 2 项 | | ⬜ | |
| **总计 24 个手动用例** | | ⬜ | |
