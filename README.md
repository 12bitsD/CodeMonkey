# 学习路径规划器（Concept Tree）

输入学习目标，生成知识依赖图谱，并按依赖顺序引导学习。

当前仓库包含：
- 前端 MVP（Vite + React + Tailwind），数据层使用 LocalStorage Mock
- 前后端接口与页面规格文档（`ConceptTree-DEV-/spec/`）

## 目录结构

```
ConceptTree-DEV-/
  frontend/          # 前端工程（可运行）
  spec/              # 规格文档（前端/后端接口）
Demo.html            # 试验文件
```

## 技术栈

- React 18
- Vite 4
- Tailwind CSS 3
- React Router（当前前端工程内未引入路由依赖；根目录另有 package.json）

## 本地运行（前端）

```bash
cd ConceptTree-DEV-/frontend
npm install
npm run dev
```

常用脚本：

```bash
npm run build
npm run preview
npm run lint
```

## Mock 数据说明

前端 API 层使用 LocalStorage 模拟后端，主要逻辑在：
- `ConceptTree-DEV-/frontend/src/services/api.js`

规格文档中定义了未来对接的真实接口（后端尚未在本仓库实现）：
- `ConceptTree-DEV-/spec/后端-通用规范.md`
- `ConceptTree-DEV-/spec/后端-首页.md`
- `ConceptTree-DEV-/spec/后端-图谱页.md`
- `ConceptTree-DEV-/spec/后端-我的学习页.md`
- `ConceptTree-DEV-/spec/后端-认证与用户.md`


```
