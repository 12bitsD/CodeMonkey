# ConceptTree - Harness Engineering 更新计划
## AI 学习助手联网搜索升级

> 生成日期：2026-04-17
> 范围：仅针对 AI 学习助手聊天能力，不改动图谱生成主链路

---

## 目标

为 AI 学习助手增加“联网搜索增强”能力，让聊天助手在回答需要最新信息、外部资料或来源引用的问题时，可以：

- 先搜索可信网页结果
- 再基于搜索结果生成回答
- 在前端展示来源链接
- 在搜索失败时自动降级为普通聊天

核心原则：

- 默认安全
- 默认可降级
- 默认可测试
- 默认不影响现有图谱生成链路

---

## 为什么适合当前架构

当前链路已经具备良好的插入点：

- `frontend/src/pages/GraphPage.jsx`
  负责 AI 聊天助手 UI 和 SSE 消费
- `backend/routers/ai.py`
  提供 `/api/ai/chat` SSE 接口
- `backend/services/ai_service.py`
  负责聊天 prompt 和上下文拼装
- `backend/services/llm/client.py`
  负责统一 LLM 调用和 fallback

因此最合理的做法不是重写聊天助手，而是在 `AIService.chat_stream` 调用 LLM 之前插入一个“搜索增强层”。

---

## 产品策略

### 第一阶段产品策略

联网搜索只服务于 AI 学习助手，不进入：

- 图谱生成
- clarify goal
- recommend-next
- explain-topic

### 搜索触发策略

第一版建议采用“显式开启优先”：

- 聊天输入框旁新增“联网搜索”开关
- 默认关闭
- 用户开启后，本次提问使用搜索增强

后续可演进为“显式开启 + 后端启发式判定”：

- 当问题包含“最新”“论文”“出处”“官网”“对比”“今天”“最近”等特征时，后端可建议搜索

---

## 架构方案

### 目标架构

```text
Frontend Chat UI
  -> POST /api/ai/chat
  -> backend/routers/ai.py
  -> AIService.chat_stream(...)
  -> SearchService.search(...)   (optional)
  -> UnifiedLLMClient.chat_stream(...)
  -> SSE chunks + sources event
```

### 关键设计

1. 搜索层独立为 `SearchService`
2. 聊天层只消费结构化搜索结果，不直接依赖某个搜索供应商
3. SSE 协议增加 `sources` 事件
4. 搜索失败时不报错中断，自动降级为无搜索聊天

---

## 代码改动计划

### Backend

#### 1. 新增搜索配置

新增配置项：

- `SEARCH_ENABLED`
- `SEARCH_PROVIDER`
- `SEARCH_API_KEY`
- `SEARCH_TIMEOUT`
- `SEARCH_MAX_RESULTS`
- `SEARCH_ALLOWED_DOMAINS`

建议位置：

- `backend/config.py`
- `backend/.env.example`

#### 2. 新增 SearchService

新增文件建议：

- `backend/services/search_service.py`

职责：

- 接收 query
- 调用外部搜索 API
- 清洗并返回统一结构

统一返回格式建议：

```python
[
  {
    "title": "...",
    "url": "...",
    "snippet": "...",
    "source": "..."
  }
]
```

#### 3. 扩展 ChatRequest

在聊天请求模型中新增字段：

- `enableWebSearch: bool = False`

建议位置：

- `backend/models.py`

#### 4. 扩展 AIService.chat_stream

在 `chat_stream` 中增加：

- 判断是否启用联网搜索
- 如果启用，先调用 `SearchService.search`
- 将搜索结果拼进 system prompt 或单独 context block
- 再调用 `llm_client.chat_stream`

建议 prompt 结构：

```text
[系统角色]
[节点/计划上下文]
[联网搜索结果摘要]
[要求：优先依据搜索结果回答，并明确不确定性]
```

#### 5. 扩展 SSE 协议

当前 `/api/ai/chat` 已经是 SSE。
建议新增事件：

- `type: "sources"`：返回搜索来源数组
- `type: "search_status"`：返回 `searching / done / fallback`

示例：

```json
{"type":"search_status","status":"searching"}
{"type":"sources","sources":[{"title":"...","url":"..."}]}
{"type":"chunk","text":"..."}
{"type":"done"}
```

#### 6. 搜索失败自动降级

需要满足：

- 搜索超时不直接报错
- 搜索返回空结果时继续普通聊天
- 搜索 API 出错时记录 warning 日志，但仍返回 AI 回答

---

### Frontend

#### 1. 聊天输入区新增联网搜索开关

建议位置：

- `frontend/src/pages/GraphPage.jsx`

交互要求：

- 开关默认关闭
- 用户提问时随请求一起发送
- 发送后不影响现有聊天流程

#### 2. 增加搜索中状态提示

在消息区显示：

- “正在联网搜索资料...”
- 搜索完成后显示来源卡片

#### 3. 展示引用来源

在 AI 回复气泡下方展示来源：

- 标题
- 域名
- 可点击链接

视觉要求：

- 来源卡片和回答内容分层
- 不喧宾夺主
- 手机端仍能正常折行

#### 4. 失败降级体验

如果搜索失败：

- 不要显示报错中断聊天
- 只提示“未获取到外部资料，已切换为普通回答”

---

## Harness Engineering 守门策略

### Hook A - Search 配置守门

当修改搜索相关配置时，自动提醒：

- 不要把真实 `SEARCH_API_KEY` 写入仓库
- 只允许写入 `.env.example`

### Hook B - 搜索结果结构守门

当修改 `search_service.py` 或 `ai.py` 时，自动检查：

- 返回结果是否仍为结构化数组
- 是否包含 `title/url/snippet`

### Hook C - SSE 协议守门

当修改 `/api/ai/chat` 时自动检查：

- `StreamingResponse` 是否仍保留
- 是否仍会输出 `done`
- 新增 `sources/search_status` 时不破坏旧 chunk 事件

### Hook D - 前端 lint 守门

修改聊天页时自动执行：

- `npx eslint`
- 指定聊天相关测试

---

## 测试计划

### Backend tests

新增建议：

- `backend/tests/test_search_service.py`
- `backend/tests/test_chat_web_search.py`

覆盖点：

- 搜索结果格式化正确
- 搜索超时自动降级
- 搜索空结果自动降级
- `/api/ai/chat` 在启用搜索时返回 `sources`
- `/api/ai/chat` 在搜索失败时仍然正常输出 `chunk/done`

### Frontend tests

新增建议：

- `frontend/src/pages/GraphPage.chat-search.test.jsx`

覆盖点：

- 开关状态切换
- 请求 payload 包含 `enableWebSearch`
- 能渲染来源卡片
- 搜索失败降级提示正常显示

### 验证脚本

新增脚本建议：

- `scripts/test_chat_web_search.ps1`

建议脚本内容：

```powershell
python -m pytest tests/test_search_service.py -q
python -m pytest tests/test_chat_web_search.py -q
npx vitest run src/pages/GraphPage.chat-search.test.jsx --pool=threads
npx eslint src/pages/GraphPage.jsx src/services/api.js
```

---

## 上线策略

### Phase 1

只做基础联网搜索：

- 前端显式开关
- 后端搜索增强
- 搜索失败自动降级
- 来源展示

### Phase 2

增加搜索质量控制：

- 白名单域名
- 结果去重
- 结果摘要压缩
- 问题类型启发式搜索

### Phase 3

扩展到解释型能力：

- `explain-topic` 支持可选外部来源增强
- 论文/官方文档优先级策略

---

## 风险与应对

### 风险 1：回答延迟增加

应对：

- 搜索请求设短超时
- 结果数限制在 3-5 条
- 超时即降级

### 风险 2：来源质量不稳定

应对：

- 首版支持域名白名单
- 提示“外部资料仅供参考”

### 风险 3：SSE 协议变更导致前端兼容问题

应对：

- 保留原有 `chunk/done`
- 新事件类型只做增量扩展

### 风险 4：搜索成本上升

应对：

- 仅显式开启时调用
- 后端增加简单缓存

---

## 验收标准

- 用户可在 AI 学习助手中开启联网搜索
- 搜索开启后，聊天接口能正常返回外部来源
- AI 回复在前端可显示来源卡片
- 搜索失败时，聊天仍能正常完成
- 现有普通聊天不受影响
- 相关前后端测试与 lint 通过

---

## 推荐执行顺序

1. 补配置与 `SearchService`
2. 扩展 `ChatRequest` 与 `AIService.chat_stream`
3. 扩展 `/api/ai/chat` 的 SSE 事件
4. 前端接入开关、搜索提示、来源展示
5. 补后端测试、前端测试、脚本
6. 小范围本地验证后再决定是否推广到 `explain-topic`

