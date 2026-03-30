# Epic 5: 统计

## 用户故事

### US-5.1 学习统计概览
**作为** 学习者  
**我想要** 查看学习统计  
**以便于** 了解学习进度

**API:** `GET /api/stats/overview`

**AC**:
- 返回总计划数 (active)
- 返回已完成计划数
- 返回已掌握知识点数
- 返回笔记数
- 返回本周学习天数

---

### US-5.2 知识领域分布
**作为** 学习者  
**我想要** 查看知识分布  
**以便于** 了解学习偏向

**API:** `GET /api/stats/distribution`

**AC**:
- 按 domain 分组
- 返回每个领域的已学习节点数
- 返回百分比

---

## 统计数据

```typescript
interface StatsOverview {
  activePlans: number;
  completedPlans: number;
  masteredKnowledgeCount: number;
  notesCount: number;
  weeklyActivity: number;  // 本周学习天数
}

interface StatsDistribution {
  distributions: {
    domain: string;
    learned: number;
    total: number;
    percentage: number;
  }[];
}
```
