# ConceptTree 项目文件整理报告

**整理日期**: 2026-03-18  
**整理人**: AI助手  
**整理前大小**: ~430MB  
**整理后大小**: ~426MB (减少约4MB临时/无用文件)

---

## 一、已删除文件清单

### 1. 系统文件
| 文件/目录 | 数量 | 说明 |
|-----------|------|------|
| `.DS_Store` | 16个 | macOS系统文件 |

### 2. 测试数据库文件
| 文件 | 大小 | 说明 |
|------|------|------|
| `test_ai.db` | 80KB | 测试数据库 |
| `test_simple.db` | 60KB | 测试数据库 |

### 3. 缓存和临时目录
| 目录 | 说明 |
|------|------|
| `.pytest_cache/` | Python测试缓存 |
| `.ruff_cache/` | Ruff代码检查缓存 |
| `.sisyphus/` | Sisyphus临时工作目录 |
| `backend/.pytest_cache/` | 后端测试缓存 |

### 4. 误放的NPM文件(根目录)
| 文件/目录 | 说明 |
|-----------|------|
| `node_modules/` | 应该在frontend目录下 |
| `package.json` | 应该在frontend目录下 |
| `package-lock.json` | 应该在frontend目录下 |

### 5. 运行时环境
| 目录 | 说明 |
|------|------|
| `.node_runtime/` | Node运行时(可由系统自动安装) |

### 6. AI工作文档
| 目录 | 文件数 | 说明 |
|------|--------|------|
| `.trae/documents/` | 6个md文件 | Trae AI工作文档 |

---

## 二、已移动文件

### 测试脚本重新组织
| 原位置 | 新位置 | 说明 |
|--------|--------|------|
| `backend/test_api_manual.py` | `backend/tests/manual/test_api_manual.py` | 手动测试脚本 |
| `backend/test_docs_sync.py` | `backend/tests/test_docs_sync.py` | 文档同步测试 |

---

## 三、整理后项目结构

```
CodeMonkey/
├── .git/                      # Git仓库
├── .gitignore                 # Git忽略配置
├── .trae/                     # Trae配置(仅保留rules/)
│   └── rules/
├── .vscode/                   # VSCode配置
├── ConceptTree/               # 主项目目录
│   ├── backend/               # 后端服务
│   │   ├── .env               # 环境变量
│   │   ├── .env.example       # 环境变量示例
│   │   ├── config.py          # 配置模块
│   │   ├── database.py        # 数据库连接
│   │   ├── main.py            # FastAPI入口
│   │   ├── models.py          # Pydantic模型
│   │   ├── pytest.ini         # Pytest配置
│   │   ├── requirements.txt   # Python依赖
│   │   ├── schema.sql         # 数据库Schema
│   │   ├── routers/           # API路由
│   │   │   ├── __init__.py
│   │   │   ├── ai.py
│   │   │   ├── auth.py
│   │   │   ├── graph.py
│   │   │   ├── notes.py
│   │   │   ├── plans.py
│   │   │   ├── stats.py
│   │   │   └── user.py
│   │   ├── scripts/           # 工具脚本
│   │   │   └── apply_schema.py
│   │   ├── services/          # 业务服务
│   │   │   ├── ai_service.py
│   │   │   ├── learning_history.py
│   │   │   └── llm/           # LLM服务
│   │   │       ├── __init__.py
│   │   │       ├── client.py
│   │   │       ├── configs/   # Prompt配置
│   │   │       │   ├── clarify_goal.json
│   │   │       │   ├── generate_graph.json
│   │   │       │   ├── parse_goal.json
│   │   │       │   └── recommend_next.json
│   │   │       └── providers/
│   │   ├── tests/             # 测试目录
│   │   │   ├── conftest.py
│   │   │   ├── manual/        # 手动测试
│   │   │   │   └── test_api_manual.py
│   │   │   ├── unit/          # 单元测试
│   │   │   │   └── ...
│   │   │   └── test_*.py      # 集成测试
│   │   ├── utils/             # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── id_generator.py
│   │   │   └── password.py
│   │   └── venv/              # Python虚拟环境
│   ├── frontend/              # 前端应用
│   │   ├── .env.example
│   │   ├── .eslintrc.json
│   │   ├── index.html
│   │   ├── node_modules/      # Node依赖
│   │   ├── package.json
│   │   ├── package-lock.json
│   │   ├── playwright.config.js
│   │   ├── postcss.config.js
│   │   ├── tailwind.config.js
│   │   ├── vite.config.js
│   │   ├── dist/              # 构建输出
│   │   ├── src/               # 源代码
│   │   │   ├── App.jsx
│   │   │   ├── main.jsx
│   │   │   ├── index.css
│   │   │   ├── components/    # 组件
│   │   │   ├── config/        # 配置
│   │   │   ├── constants/     # 常量
│   │   │   ├── contexts/      # 状态管理
│   │   │   ├── hooks/         # 自定义Hooks
│   │   │   ├── pages/         # 页面
│   │   │   ├── services/      # API服务
│   │   │   ├── types/         # 类型定义
│   │   │   └── utils/         # 工具函数
│   │   ├── test-results/      # 测试结果
│   │   └── tests/             # E2E测试
│   └── spec/                  # 规范文档
│       ├── 进度总览.md
│       ├── 前端-架构总览.md
│       ├── 后端-通用规范.md
│       └── ...
├── docs/                      # 项目文档
│   ├── project-code-review-report-2026-03-18.md
│   └── superpowers/
├── supabase/                  # Supabase配置
│   └── migrations/
├── AI服务Mermaid图解.md       # 架构图
├── ConceptTree-Architecture.md # 架构文档
├── LICENSE                    # 许可证
├── README.md                  # 项目说明
├── start-dev.sh               # 启动脚本
└── 学习路径规划器 - MVP PRD（最终版）.md  # PRD文档
```

---

## 四、.gitignore配置说明

已配置的忽略项包括：

```
# Python
__pycache__/
*.py[cod]

# Virtual Environment
venv/

# Secrets
.env

# Database
*.sqlite
*.db

# IDE
.vscode/
.idea/
.trae/documents/

# OS
.DS_Store

# Testing
.pytest_cache/

# Node
node_modules/

# Runtime
.node_runtime/
```

---

## 五、文件分类统计

| 类别 | 文件数 | 说明 |
|------|--------|------|
| 业务代码 | ~60个 | Python/JSX/JS |
| 配置文件 | ~15个 | JSON/YAML/SQL |
| 测试文件 | ~25个 | Python/JS |
| 文档文件 | ~15个 | Markdown |
| 依赖目录 | 2个 | venv/, node_modules/ |

---

## 六、建议

### 保持整洁的建议

1. **定期清理**
   - 每周运行: `find . -name ".DS_Store" -delete`
   - 清理测试数据库: `rm -f *.db`

2. **避免提交**
   - 确保 `.gitignore` 包含所有临时/缓存文件
   - 不要提交 `venv/` 或 `node_modules/`

3. **文档管理**
   - AI工作文档放在 `.trae/documents/` 并已加入 `.gitignore`
   - 重要文档放在 `docs/` 目录

4. **测试组织**
   - 手动测试脚本放在 `tests/manual/`
   - 单元测试放在 `tests/unit/`
   - 集成测试直接放在 `tests/`

---

**整理完成** ✅

项目现在更加干净整洁，易于维护。
