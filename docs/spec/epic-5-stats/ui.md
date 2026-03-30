# Epic 5: 前端需求

## 页面: 我的学习 (`/my-learning`)

### Tab: 统计

**US-5.1 概览统计**
- 活跃计划数
- 已完成计划数
- 掌握知识数
- 笔记数
- 本周学习天数

**US-5.2 领域分布**
- 饼图/柱状图显示各领域占比
- 按 domain 分组

### 组件

```
MyLearningPage
└── StatsTab
    ├── OverviewSection
    │   ├── StatCard (活跃计划)
    │   ├── StatCard (已完成)
    │   ├── StatCard (掌握知识)
    │   ├── StatCard (笔记)
    │   └── StatCard (本周学习)
    └── DistributionSection
        └── ChartBar (各领域分布)
```

---

## API 调用

```javascript
// 获取统计概览
statsApi.getOverview()

// 获取领域分布
statsApi.getDistribution()
```
