# Epic 2: 图谱核心

## 用户故事

### US-2.1 创建学习计划
**作为** 学习者  
**我想要** 创建学习计划  
**以便于** 开始学习路径

**API:** `POST /api/plans`

**AC**:
- 标题必填
- 必须包含节点列表
- 必须包含边列表
- 返回 planId

---

### US-2.2 获取计划列表
**作为** 学习者  
**我想要** 查看我的计划列表  
**以便于** 选择学习内容

**API:** `GET /api/plans`

**AC**:
- 仅返回当前用户的计划
- 支持按状态筛选 (active/archived)
- 按 last_access_at 降序排列

---

### US-2.3 获取图谱
**作为** 学习者  
**我想要** 查看图谱详情  
**以便于** 了解知识依赖

**API:** `GET /api/plans/{plan_id}/graph`

**AC**:
- 验证 plan_id 存在且属于当前用户
- 返回 plan 信息
- 返回所有节点
- 返回所有边

---

### US-2.4 更新节点状态
**作为** 学习者  
**我想要** 标记节点学习状态  
**以便于** 追踪进度

**API:** `PUT /api/plans/{plan_id}/nodes/{node_id}/status`

**状态值**: `unlearned` | `learned` | `skipped`

**AC**:
- 更新 nodes.status
- 更新 plans.progress (已学习数)
- 插入 learning_sessions 记录
- 若 status='learned': 更新 user_profiles.mastered_knowledge

---

### US-2.5 保存节点位置
**作为** 学习者  
**我想要** 调整节点位置  
**以便于** 自定义图谱布局

**API:** `PUT /api/plans/{plan_id}/nodes/{node_id}/position`

**AC**:
- 更新 nodes.x, nodes.y
- 支持拖拽后的批量保存

---

### US-2.6 批量保存节点位置
**作为** 学习者  
**我想要** 一次性保存所有调整  
**以便于** 减少 API 调用

**API:** `PUT /api/plans/{plan_id}/nodes/positions`

**AC**:
- 批量更新多个节点位置
- 事务处理

---

### US-2.7 更新计划标题
**作为** 学习者  
**我想要** 修改计划标题  
**以便于** 更好识别

**API:** `PUT /api/plans/{plan_id}`

**AC**:
- 仅更新 title 字段

---

### US-2.8 归档计划
**作为** 学习者  
**我想要** 归档不活跃的计划  
**以便于** 保持列表整洁

**API:** `PUT /api/plans/{plan_id}/archive`

**AC**:
- plans.status = 'archived'

---

### US-2.9 恢复计划
**作为** 学习者  
**我想要** 恢复归档的计划  
**以便于** 继续学习

**API:** `PUT /api/plans/{plan_id}/restore`

**AC**:
- plans.status = 'active'

---

### US-2.10 删除计划
**作为** 学习者  
**我想要** 删除废弃计划  
**以便于** 清理空间

**API:** `DELETE /api/plans/{plan_id}`

**AC**:
- 级联删除 nodes, edges, notes, learning_sessions

---

## 节点数据结构

```typescript
interface Node {
  id: string;
  name: string;
  status: 'unlearned' | 'learned' | 'skipped';
  x: number;
  y: number;
  why: string;       // 为什么学
  what: string[];    // 学什么
  mastery: string[];  // 掌握标准
  prompt: string;     // 学习提示
  resources: Resource[];
  isTarget: boolean;  // 是否目标节点
  domain: string;     // 知识领域
}

interface Edge {
  from: string;       // 前端: from_node
  to: string;         // 前端: to_node
}
```

---

## 图谱布局算法

节点位置由 LLM 生成，初次生成后由用户拖拽调整。

---

## 进度计算

```
progress = count(nodes WHERE status = 'learned')
total = count(nodes WHERE status != 'skipped')
```
