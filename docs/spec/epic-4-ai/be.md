# Epic 4: AI 服务

## 用户故事

### US-4.1 解析学习目标
**作为** 学习者  
**我想要** AI 解析我的学习目标  
**以便于** 了解 AI 的理解

**API:** `POST /api/ai/parse-goal`

**AC**:
- 返回 interpretation (AI 对目标的理解)
- 返回 backgroundSummary (背景摘要)
- 若目标太大，返回 shouldSplit=true 和拆分建议

---

### US-4.2 生成知识图谱
**作为** 学习者  
**我想要** AI 生成学习图谱  
**以便于** 获得学习路径

**API:** `POST /api/ai/generate-graph`

**AC**:
- 考虑用户背景 (编程水平/数学水平/已掌握知识)
- 生成节点列表 (含 what, why, mastery, resources)
- 生成边列表 (依赖关系)
- 返回 targetNodeId (最终目标节点)

---

### US-4.3 澄清/调整目标
**作为** 学习者  
**我想要** 调整图谱  
**以便于** 更符合我的需求

**API:** `POST /api/ai/clarify-goal`

**AC**:
- 接受原始目标和调整描述
- 携带现有节点上下文
- 返回 isLargeChange (是否大幅调整)
- 返回 changes (keep/remove/add)

---

### US-4.4 AI 推荐下一节点
**作为** 学习者  
**我想要** AI 推荐下一个学习节点  
**以便于** 知道该学什么

**API:** `POST /api/ai/recommend-next`

**AC**:
- 考虑学习历史 (learning_sessions)
- 考虑用户画像 (编程/数学水平)
- 优先推荐依赖已满足的节点
- 若无推荐，返回 reason

---

### US-4.5 应用图谱变更
**作为** 学习者  
**我想要** 应用调整到图谱  
**以便于** 保存修改

**API:** `POST /api/plans/{plan_id}/apply-changes`

**AC**:
- 删除 keep 以外的节点
- 新增 add 列表中的节点
- 更新标题 (如需要)

---

## AI 服务架构

```
routers/ai.py
    ↓
services/ai_service.py
    ↓
services/llm/client.py (UnifiedLLMClient)
    ↓
services/llm/providers/openai_compatible.py (Kimi)
```

### Prompt 配置

| Action | Config File |
|--------|-------------|
| parse-goal | `services/llm/configs/parse_goal.json` |
| generate-graph | `services/llm/configs/generate_graph.json` |
| clarify-goal | `services/llm/configs/clarify_goal.json` |
| recommend-next | `services/llm/configs/recommend_next.json` |

---

## LLM 配置

- 模型: Kimi 2.5 (moonshot-v1-8k)
- Base URL: `https://api.moonshot.cn/v1`
- 备用: OpenAI API (可选)
