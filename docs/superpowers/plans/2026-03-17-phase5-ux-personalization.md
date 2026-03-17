# Phase 5: UX完善 + 个性化图谱 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐三个关键缺口：全局错误反馈（Toast）、用户画像传入 AI 生成个性化图谱、目标调整（clarify-goal）功能。

**Architecture:**
- Chunk 1 仅改前端：新建 `ToastContext` + `useToast` hook，App.jsx 挂载，替换全部 `alert()` 和沉默 `console.error`。
- Chunk 2 前后端联动：前端把 `userProfile` 带入 `generate-graph` 请求体，后端 router 从 DB 拉取用户画像并传给 AI Service，AI Service 将画像格式化注入 prompt。
- Chunk 3 新增 `clarify-goal` 后端端点 + 前端"修改目标"流程：用户输入新目标 → AI 判断变更幅度 → 若大改则引导新建计划，若小改则确认后覆盖重生成。

**Tech Stack:** React 18 + Vite + FastAPI + Pydantic + Kimi LLM

---

## 当前状态 Baseline

| 项目 | 状态 | 说明 |
|------|------|------|
| Toast / 错误提示 | ❌ 缺失 | alert() + console.error，用户无感知 |
| 全局 Loading | ❌ 缺失 | 长操作无全局反馈 |
| user_background 传递 | ❌ 缺失 | 后端硬编码 `user_background=None` |
| clarify-goal | ❌ 缺失 | 后端无端点，前端无 UI |
| recommend-next | ✅ 已实现 | 前端规则引擎，无需后端 |

---

## Chunk 1: 全局 Toast 通知系统

### Task 1.1: 创建 ToastContext

**Files:**
- Create: `ConceptTree/frontend/src/contexts/ToastContext.jsx`
- Modify: `ConceptTree/frontend/src/App.jsx`

- [ ] **Step 1: 创建 ToastContext.jsx**

```jsx
import React, { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration);
  }, []);

  const toast = {
    success: (msg) => addToast(msg, 'success'),
    error: (msg) => addToast(msg, 'error'),
    info: (msg) => addToast(msg, 'info'),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} />
    </ToastContext.Provider>
  );
}

function ToastContainer({ toasts }) {
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-6 right-6 flex flex-col gap-2 z-50">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`px-4 py-3 rounded-xl text-sm font-medium shadow-lg transition-all ${
            t.type === 'error' ? 'bg-red-600 text-white' :
            t.type === 'success' ? 'bg-teal-600 text-white' :
            'bg-zinc-800 text-white'
          }`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
```

- [ ] **Step 2: 挂载 ToastProvider 到 App.jsx**

打开 `ConceptTree/frontend/src/App.jsx`，找到根组件结构，在最外层包裹 `ToastProvider`：

```jsx
import { ToastProvider } from './contexts/ToastContext';

function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </AppProvider>
    </AuthProvider>
  );
}
```

（具体层级视当前 App.jsx 实际代码调整，关键是 ToastProvider 在所有页面组件之上）

- [ ] **Step 3: 验证 ToastProvider 可用**

```bash
cd ConceptTree/frontend
npm run dev
```

打开浏览器控制台，执行：
```javascript
// 预期不报错，app 正常渲染
```

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/frontend/src/contexts/ToastContext.jsx ConceptTree/frontend/src/App.jsx
git commit -m "feat(frontend): add global ToastProvider with success/error/info variants"
```

---

### Task 1.2: 替换 HomePage 的错误处理

**Files:**
- Modify: `ConceptTree/frontend/src/pages/HomePage.jsx`

- [ ] **Step 1: 引入 useToast**

在 HomePage.jsx 顶部加：
```jsx
import { useToast } from '../contexts/ToastContext';
```

在组件内：
```jsx
const toast = useToast();
```

- [ ] **Step 2: 替换 alert() 和 console.error**

找到以下三处，替换：

```jsx
// 原 handleStartAnalysis catch
} catch (error) {
  console.error("Analysis failed", error);
}
// 替换为：
} catch (error) {
  toast.error('解析目标失败，请稍后重试');
}

// 原 handleConfirmGeneration catch
} catch (error) {
  console.error("Generation failed", error);
  setIsGenerating(false);
}
// 替换为：
} catch (error) {
  toast.error('生成图谱失败，请稍后重试');
  setIsGenerating(false);
}

// 原 handleLogin alert
alert(result.error || '登录失败');
// 替换为：
toast.error(result.error || '登录失败');

// 原 handleLogin register alert
alert(result.error || '注册失败');
// 替换为：
toast.error(result.error || '注册失败');

// 原 catch(error) alert
alert('操作失败，请重试');
// 替换为：
toast.error('操作失败，请重试');
```

- [ ] **Step 3: 验证 E2E 错误状态测试仍通过**

```bash
cd ConceptTree/frontend
npx playwright test tests/main-flow.spec.js -k "error state" --project=chromium
```

Expected: 1 passed

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/frontend/src/pages/HomePage.jsx
git commit -m "fix(frontend): replace alert/console.error with toast notifications in HomePage"
```

---

### Task 1.3: 替换 AppContext 的错误处理

**Files:**
- Modify: `ConceptTree/frontend/src/contexts/AppContext.jsx`

- [ ] **Step 1: 引入 useToast 并替换所有 console.error**

AppContext.jsx 里有多处 `console.error('归档计划失败', error)` 等。

引入 toast：
```jsx
import { useToast } from './ToastContext';
```

在 AppProvider 组件内：
```jsx
const toast = useToast();
```

替换所有 `console.error` 为 `toast.error`：

| 原代码 | 替换为 |
|--------|--------|
| `console.error('归档计划失败', error)` | `toast.error('归档计划失败')` |
| `console.error('删除计划失败', error)` | `toast.error('删除计划失败')` |
| `console.error('添加笔记失败', error)` | `toast.error('添加笔记失败')` |
| `console.error('更新用户画像失败', error)` | `toast.error('更新用户画像失败')` |

（搜索 `console.error` 替换所有实例）

- [ ] **Step 2: 运行全量 E2E 测试**

```bash
cd ConceptTree/frontend
npx playwright test tests/main-flow.spec.js --project=chromium
```

Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add ConceptTree/frontend/src/contexts/AppContext.jsx
git commit -m "fix(frontend): replace console.error with toast notifications in AppContext"
```

---

## Chunk 2: 用户画像传入图谱生成

### Task 2.1: 前端 graphApi.generate 传递 userProfile

**Files:**
- Modify: `ConceptTree/frontend/src/services/api.js`

当前 `graphApi.generate` 只传 `input`，但 HomePage 调用时已传 `userProfile` 作为第二参数：
```javascript
graphApi.generate(inputText, userProfile)  // userProfile 被忽略
```

- [ ] **Step 1: 修改 graphApi.generate 接受并传递 userProfile**

在 `api.js` 中找到 `graphApi.generate`，改为：

```javascript
generate: async (input, userProfile = null) => {
  const body = { input, interpretation: input };
  if (userProfile) {
    body.userBackground = {
      occupation: userProfile.occupation || '',
      education: userProfile.education || '',
      programmingLevel: userProfile.programmingLevel || '',
      mathLevel: userProfile.mathLevel || '',
      abilities: userProfile.abilities || [],
      masteredKnowledge: userProfile.masteredKnowledge || [],
    };
  }
  const result = await fetchApi("/ai/generate-graph", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return {
    ...result,
    edges: mapEdgesFromBackend(result.edges),
  };
},
```

- [ ] **Step 2: 同样更新 aiApi.parseGoal 传递用户背景（可选优化）**

找到 `aiApi.parseGoal`，在请求体中加入用户背景让 AI 理解用户当前能力：

```javascript
parseGoal: async (input, userProfile = null) => {
  const body = { input };
  if (userProfile?.abilities?.length || userProfile?.masteredKnowledge?.length) {
    body.userBackground = {
      abilities: userProfile.abilities || [],
      masteredKnowledge: userProfile.masteredKnowledge || [],
    };
  }
  return await fetchApi("/ai/parse-goal", {
    method: "POST",
    body: JSON.stringify(body),
  });
},
```

- [ ] **Step 3: Commit**

```bash
git add ConceptTree/frontend/src/services/api.js
git commit -m "feat(frontend): pass userProfile to generate-graph and parse-goal requests"
```

---

### Task 2.2: 后端 GenerateGraphRequest 接收 userBackground

**Files:**
- Modify: `ConceptTree/backend/routers/ai.py`
- Modify: `ConceptTree/backend/models.py`（添加 UserBackgroundInput model）

- [ ] **Step 1: 在 models.py 添加 UserBackgroundInput**

在 `ConceptTree/backend/models.py` 中添加：

```python
class UserBackgroundInput(BaseModel):
    occupation: str = ""
    education: str = ""
    programmingLevel: str = ""
    mathLevel: str = ""
    abilities: List[str] = []
    masteredKnowledge: List[str] = []
```

- [ ] **Step 2: 更新 GenerateGraphRequest**

在 `routers/ai.py` 中，修改 `GenerateGraphRequest`：

```python
from models import UserBackgroundInput

class GenerateGraphRequest(BaseModel):
    input: str
    interpretation: str
    userBackground: Optional[UserBackgroundInput] = None
```

同时在 `generate_graph` 端点中，将 `userBackground` 传给 AI Service：

```python
@router.post("/generate-graph", ...)
async def generate_graph(
    request: GenerateGraphRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    ai_service = get_ai_service()
    
    user_bg = None
    if request.userBackground:
        user_bg = request.userBackground.model_dump()
    
    result = await ai_service.generate_graph(
        interpretation=request.interpretation,
        original_input=request.input,
        user_background=user_bg,
    )
    ...
```

- [ ] **Step 3: 验证后端不报错（无 API Key 时 skip）**

```bash
cd ConceptTree/backend
source venv/bin/activate
python3 -c "
from routers.ai import GenerateGraphRequest
from models import UserBackgroundInput
req = GenerateGraphRequest(
    input='学Python',
    interpretation='掌握Python基础',
    userBackground=UserBackgroundInput(abilities=['JavaScript入门'], masteredKnowledge=['变量'])
)
print('Request OK:', req.userBackground.abilities)
"
```

Expected: `Request OK: ['JavaScript入门']`

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/backend/routers/ai.py ConceptTree/backend/models.py
git commit -m "feat(backend): accept userBackground in generate-graph request and pass to AI service"
```

---

### Task 2.3: 更新 generate-graph prompt 使用 userBackground

**Files:**
- Modify: `ConceptTree/backend/services/llm/configs/generate_graph.json`

当前 `generate_graph.json` 的 `system_prompt` 没有提到用户背景。`background` 变量通过 `load_ai_config` 的 kwargs 注入，但规则里没有明确指导 AI 如何使用。

- [ ] **Step 1: 更新 generate_graph.json 的 rules 和 system_prompt**

在 `generate_graph.json` 的 `rules` 数组末尾追加：

```json
"Background Adaptation (CRITICAL): Read the user background carefully. If 'masteredKnowledge' contains knowledge that overlaps with prerequisite nodes, mark those nodes status as 'skipped' instead of 'unlearned'. If 'abilities' show strong foundation in an area, reduce nodes in that area or increase their depth. If weaknesses exist, add foundational nodes."
```

同时确认 `system_prompt` 提到了用户背景的重要性：
```json
"system_prompt": "You are an AI learning assistant. Generate a personalized knowledge dependency graph for the given learning goal, taking the user's background into account to skip already-mastered prerequisites and adjust depth appropriately."
```

- [ ] **Step 2: 验证 JSON 语法**

```bash
cd ConceptTree/backend
python3 -c "import json; json.load(open('services/llm/configs/generate_graph.json')); print('JSON valid')"
```

Expected: `JSON valid`

- [ ] **Step 3: 运行后端测试（无 API Key skip）**

```bash
cd ConceptTree/backend
source venv/bin/activate
python3 -m pytest tests/test_ai_integration.py -v -q 2>&1 | head -20
```

Expected: tests skip or pass (no import errors)

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/backend/services/llm/configs/generate_graph.json
git commit -m "feat(llm): update generate-graph prompt to personalize based on user background and mastered knowledge"
```

---

## Chunk 3: clarify-goal — 目标调整功能

### Task 3.1: 后端 clarify-goal 端点

**Files:**
- Modify: `ConceptTree/backend/routers/ai.py`
- Modify: `ConceptTree/backend/services/ai_service.py`
- Create: `ConceptTree/backend/services/llm/configs/clarify_goal.json`

clarify-goal 的职责：接收「当前目标」和「新目标」，判断变更幅度并给出建议。
- 返回 `is_large_change: bool`（变化大则建议新建计划）
- 返回 `interpretation: str`（对新目标的理解）
- 返回 `suggestion: "modify" | "create_new"`

- [ ] **Step 1: 创建 clarify_goal.json**

创建 `ConceptTree/backend/services/llm/configs/clarify_goal.json`：

```json
{
  "model_params": {
    "temperature": 0.3,
    "max_tokens": 800
  },
  "system_prompt": "You are an AI learning assistant. Analyze how much a user's learning goal has changed and decide whether to modify the existing plan or create a new one.",
  "output_format": {
    "interpretation": "Clear, specific interpretation of the new goal (1 sentence in Chinese)",
    "isLargeChange": "true if the new goal is fundamentally different from the original (boolean)",
    "suggestion": "modify or create_new",
    "reason": "Brief explanation of why (1 sentence in Chinese)"
  },
  "rules": [
    "isLargeChange = true if: new goal is a completely different subject, OR requires 50%+ different prerequisite nodes",
    "isLargeChange = false if: new goal is a refinement, specialization, or narrowing of the original goal",
    "suggestion = 'create_new' when isLargeChange = true",
    "suggestion = 'modify' when isLargeChange = false"
  ],
  "examples": [
    {
      "input": "original: 学Python, new: 学Python数据分析",
      "output": {"interpretation": "用Python进行数据分析，掌握pandas和matplotlib", "isLargeChange": false, "suggestion": "modify", "reason": "新目标是原目标的具体化方向"}
    },
    {
      "input": "original: 学Python, new: 学Java后端开发",
      "output": {"interpretation": "使用Java开发后端服务，掌握Spring框架", "isLargeChange": true, "suggestion": "create_new", "reason": "编程语言完全不同，知识体系差异显著"}
    }
  ]
}
```

- [ ] **Step 2: 在 ai_service.py 添加 clarify_goal 方法**

在 `AIService` 类中添加（ai_service.py）：

```python
async def clarify_goal(
    self,
    original_goal: str,
    new_goal: str,
) -> "ClarifyGoalAIResult":
    try:
        combined_input = f"original: {original_goal}, new: {new_goal}"
        params, sys_prompt, usr_prompt = load_ai_config(
            "clarify_goal",
            combined_input,
        )
        result = await self.llm_client.chat_json(
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            temperature=params.get("temperature", 0.3),
            max_tokens=params.get("max_tokens", 800),
        )
        parsed = ClarifyGoalResponse(**result)
        return ClarifyGoalAIResult(success=True, data=parsed)
    except (LLMServiceError, ConfigLoadError) as e:
        return ClarifyGoalAIResult(
            success=False,
            error=ApiError(code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}"),
        )
    except Exception as e:
        return ClarifyGoalAIResult(
            success=False,
            error=ApiError(code="AI_SERVICE_ERROR", message=f"Failed to clarify goal: {str(e)}"),
        )
```

需要先在 models.py 添加：

```python
class ClarifyGoalResponse(BaseModel):
    interpretation: str
    isLargeChange: bool
    suggestion: str  # "modify" | "create_new"
    reason: str

class ClarifyGoalAIResult(BaseModel):
    success: bool
    data: Optional[ClarifyGoalResponse] = None
    error: Optional[ApiError] = None
```

并在 ai_service.py import 中加入 `ClarifyGoalResponse, ClarifyGoalAIResult`。

- [ ] **Step 3: 在 routers/ai.py 添加 clarify-goal 端点**

```python
class ClarifyGoalRequest(BaseModel):
    originalGoal: str
    newGoal: str

    @field_validator("newGoal")
    @classmethod
    def validate_new_goal(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("New goal must be at least 5 characters")
        if len(v) > 2000:
            raise ValueError("New goal must be less than 2000 characters")
        return v

class ClarifyGoalResponseWrapper(BaseModel):
    success: bool
    data: dict

@router.post(
    "/clarify-goal",
    response_model=ClarifyGoalResponseWrapper,
    responses={403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def clarify_goal(
    request: ClarifyGoalRequest,
    current_user_id: str = Depends(get_current_user_id),
    db=Depends(get_db),
):
    ai_service = get_ai_service()
    result = await ai_service.clarify_goal(
        original_goal=request.originalGoal,
        new_goal=request.newGoal,
    )
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": result.error.model_dump() if result.error else {}},
        )
    return {"success": True, "data": result.data.model_dump() if result.data else {}}
```

- [ ] **Step 4: 验证端点注册**

```bash
cd ConceptTree/backend
source venv/bin/activate
python3 -c "
from routers.ai import router
routes = [r.path for r in router.routes]
print('Routes:', routes)
assert '/api/ai/clarify-goal' in routes or any('clarify-goal' in r for r in routes)
print('clarify-goal endpoint registered OK')
"
```

Expected: `clarify-goal endpoint registered OK`

- [ ] **Step 5: Commit**

```bash
git add ConceptTree/backend/routers/ai.py ConceptTree/backend/services/ai_service.py ConceptTree/backend/models.py ConceptTree/backend/services/llm/configs/clarify_goal.json
git commit -m "feat(backend): add clarify-goal endpoint for learning goal adjustment analysis"
```

---

### Task 3.2: 前端 API 对接 + clarify-goal 流程

**Files:**
- Modify: `ConceptTree/frontend/src/services/api.js`
- Modify: `ConceptTree/frontend/src/pages/GraphPage.jsx`

- [ ] **Step 1: 添加 aiApi.clarifyGoal**

在 `api.js` 的 `aiApi` 对象中添加：

```javascript
clarifyGoal: async (originalGoal, newGoal) => {
  return await fetchApi("/ai/clarify-goal", {
    method: "POST",
    body: JSON.stringify({ originalGoal, newGoal }),
  });
},
```

- [ ] **Step 2: 在 GraphPage 添加"修改目标"交互**

在 GraphPage.jsx 中：

**2a. 添加 state：**
```jsx
const [showClarifyModal, setShowClarifyModal] = useState(false);
const [newGoalInput, setNewGoalInput] = useState('');
const [clarifyResult, setClarifyResult] = useState(null);
const [isClarifying, setIsClarifying] = useState(false);
```

**2b. 添加处理函数：**
```jsx
const handleClarifyGoal = async () => {
  if (!newGoalInput.trim() || !plan) return;
  setIsClarifying(true);
  try {
    const result = await aiApi.clarifyGoal(plan.title, newGoalInput);
    setClarifyResult(result);
  } catch (err) {
    toast.error('分析失败，请重试');
  } finally {
    setIsClarifying(false);
  }
};

const handleApplyClarify = () => {
  if (!clarifyResult) return;
  if (clarifyResult.isLargeChange) {
    navigate(`/?goal=${encodeURIComponent(newGoalInput)}`);
  } else {
    navigate(`/?goal=${encodeURIComponent(newGoalInput)}`);
  }
  setShowClarifyModal(false);
};
```

**2c. 在 GraphPage header 添加"修改目标"按钮：**

在图谱页标题区域（当前有 plan.title 显示的地方）添加：
```jsx
<button
  onClick={() => { setNewGoalInput(''); setClarifyResult(null); setShowClarifyModal(true); }}
  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-800 border border-zinc-200 rounded-full hover:border-zinc-400 transition-all"
>
  <Edit3 size={12} />
  修改目标
</button>
```

**2d. 添加 clarify Modal：**
```jsx
<Modal
  isOpen={showClarifyModal}
  onClose={() => setShowClarifyModal(false)}
  title="修改学习目标"
  footer={
    <>
      <Button variant="ghost" onClick={() => setShowClarifyModal(false)}>取消</Button>
      {!clarifyResult ? (
        <Button onClick={handleClarifyGoal} disabled={isClarifying || !newGoalInput.trim()}>
          {isClarifying ? '分析中...' : '分析变更'}
        </Button>
      ) : (
        <Button onClick={handleApplyClarify}>
          {clarifyResult.isLargeChange ? '新建计划' : '应用修改'}
        </Button>
      )}
    </>
  }
>
  <div className="space-y-4">
    <div>
      <p className="text-xs text-zinc-400 mb-2">当前目标</p>
      <p className="text-sm text-zinc-600 bg-zinc-50 px-3 py-2 rounded-lg">{plan?.title}</p>
    </div>
    <div>
      <p className="text-xs text-zinc-400 mb-2">新目标</p>
      <textarea
        className="w-full h-24 p-3 text-sm border border-zinc-200 rounded-lg resize-none outline-none focus:border-zinc-400"
        placeholder="输入修改后的学习目标..."
        value={newGoalInput}
        onChange={e => { setNewGoalInput(e.target.value); setClarifyResult(null); }}
      />
    </div>
    {clarifyResult && (
      <div className={`p-4 rounded-xl border ${clarifyResult.isLargeChange ? 'bg-amber-50 border-amber-200' : 'bg-teal-50 border-teal-200'}`}>
        <p className="text-sm font-medium mb-1">
          {clarifyResult.isLargeChange ? '🔄 目标变化较大，建议新建计划' : '✏️ 小幅调整，将更新现有图谱'}
        </p>
        <p className="text-xs text-zinc-500">{clarifyResult.reason}</p>
      </div>
    )}
  </div>
</Modal>
```

- [ ] **Step 3: 验证 E2E 全量测试**

```bash
cd ConceptTree/frontend
npx playwright test tests/main-flow.spec.js --project=chromium
```

Expected: 4 passed（已有测试不受影响）

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/frontend/src/services/api.js ConceptTree/frontend/src/pages/GraphPage.jsx
git commit -m "feat(frontend): add clarify-goal UI with change analysis and new-plan/modify flow"
```

---

## 验收标准

### Chunk 1 Done
- [ ] `alert()` 从全局消失，替换为右下角 Toast
- [ ] 错误状态（AI 500）用户可见 Toast 提示
- [ ] E2E 4 测试全通过

### Chunk 2 Done
- [ ] 前端 `graphApi.generate` 将 `userProfile` 序列化到请求体
- [ ] 后端 `generate-graph` 接收 `userBackground` 并传给 AI Service
- [ ] 有用户画像时生成的图谱已掌握节点标为 `skipped`

### Chunk 3 Done
- [ ] `POST /api/ai/clarify-goal` 返回 `{isLargeChange, suggestion, interpretation, reason}`
- [ ] GraphPage 有"修改目标"按钮 + 分析弹窗
- [ ] 大变更引导新建计划，小变更提示应用修改

---

## 优先级建议

| 优先级 | 任务 | 理由 |
|--------|------|------|
| P0 | Chunk 1 (Toast) | 当前 UX 最大痛点，实现成本极低 |
| P1 | Chunk 2 (个性化) | PRD 核心功能，后端一行代码，效果显著 |
| P2 | Chunk 3 (clarify-goal) | 差异化功能，稍复杂，可排后续 |

---

*Plan Version*: 1.0  
*Created*: 2026-03-17
