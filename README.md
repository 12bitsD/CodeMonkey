# PathFinder - 学习路径规划器

## 快速开始

### 方式 1: 使用启动脚本（推荐）

```bash
./start-dev.sh
```

这将同时启动前端和后端开发服务器。

### 方式 2: 使用 VS Code 调试配置

1. 打开 VS Code
2. 按 `Cmd+Shift+D` (macOS) 或 `Ctrl+Shift+D` (Windows/Linux)
3. 选择 `后端: FastAPI` 或 `前端: Vite 开发服务器`
4. 按 `F5` 启动

### 方式 3: 手动启动

**后端:**
```bash
cd ConceptTree/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端:**
```bash
cd ConceptTree/frontend
npm install  # 首次运行
npm run dev
```

## 访问地址

- 前端应用: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 项目结构

```
CodeMonkey/
├── ConceptTree/
│   ├── backend/          # 后端 FastAPI 应用
│   │   ├── routers/      # API 路由
│   │   ├── tests/        # 后端测试
│   │   ├── main.py       # 应用入口
│   │   ├── database.py   # 数据库配置
│   │   └── models.py     # 数据模型
│   ├── frontend/         # 前端 React 应用
│   │   ├── src/
│   │   │   ├── components/  # React 组件
│   │   │   ├── pages/       # 页面组件
│   │   │   ├── services/    # API 服务
│   │   │   └── contexts/    # React Context
│   │   └── package.json
│   └── spec/            # 项目规范文档
├── .vscode/             # VS Code 配置
│   ├── launch.json      # 调试配置
│   ├── settings.json    # 编辑器设置
│   ├── tasks.json       # 任务配置
│   └── extensions.json  # 推荐扩展
├── .trae/               # Trae 项目配置
│   ├── documents/       # 项目文档
│   └── rules/           # 项目规则
└── start-dev.sh         # 快速启动脚本
```

## 开发指南

### 后端开发

**安装依赖:**
```bash
cd ConceptTree/backend
source venv/bin/activate
pip install -r requirements.txt
```

**运行测试:**
```bash
pytest -v
```

**代码格式化:**
```bash
black .
```

**代码检查:**
```bash
flake8 .
```

### 前端开发

**安装依赖:**
```bash
cd ConceptTree/frontend
npm install
```

**运行测试:**
```bash
npm test
```

**代码检查:**
```bash
npm run lint
```

**构建生产版本:**
```bash
npm run build
```

## 调试

详细的调试配置说明请查看 [调试环境配置说明.md](.trae/documents/调试环境配置说明.md)

### VS Code 调试配置

项目已配置以下调试选项：

**后端:**
- `后端: FastAPI` - 启动 FastAPI 开发服务器
- `后端: 当前 Python 文件` - 调试当前 Python 文件
- `后端: 运行测试` - 运行并调试 pytest 测试

**前端:**
- `前端: Vite 开发服务器` - 启动 Vite 开发服务器
- `前端: Chrome 调试` - 在 Chrome 中调试前端
- `前端: 运行测试` - 运行前端测试

## API 文档

启动后端服务器后，访问 http://localhost:8000/docs 查看交互式 API 文档。

## 技术栈

**后端:**
- FastAPI - Web 框架
- Uvicorn - ASGI 服务器
- SQLite - 数据库
- Pydantic - 数据验证
- Pytest - 测试框架

**前端:**
- React 18 - UI 框架
- Vite - 构建工具
- Tailwind CSS - 样式框架
- Lucide React - 图标库

## 开发规则

请遵循 `.trae/rules/project_rules.md` 中定义的开发规则：

1. 编写代码前先阅读 `ConceptTree/spec` 中的规范
2. 确保理解一致后再开始编码
3. 优先更新 spec 文档，然后编写测试
4. 根据测试用例编写代码
5. 运行测试确保通过
6. 检查路由链路和命名一致性
7. 在 spec 中标记实现状态（✅/❌）

## 常见问题

### 后端无法启动

1. 检查虚拟环境是否激活
2. 安装依赖: `pip install -r requirements.txt`
3. 检查端口 8000 是否被占用

### 前端无法启动

1. 安装依赖: `npm install`
2. 检查 Node.js 版本（需要 16+）
3. 检查端口 5173 是否被占用

### 测试失败

1. 确保数据库文件已清理
2. 检查测试数据是否正确
3. 查看详细错误信息: `pytest -v -s`

## 许可证

MIT License
