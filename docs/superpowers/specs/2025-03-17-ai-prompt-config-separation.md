# AI Prompt Configuration Separation Spec

> **Approved Date**: 2025-03-17
> **Target**: 把原本在代码和 .txt 模板中硬编码的 System Prompt、Output Format 协议、Rules 和 LLM 调用参数，抽取为独立的 JSON 配置文件，方便非技术人员或不改代码的情况下调整 AI 行为。

---

## 1. 目标与范围

**问题现状：**
目前 `parse-goal` 和 `generate-graph` 的 prompt 是写在 `backend/services/llm/prompts/*.txt` 文件里的 Jinja2 模板，混合了大量关于数据结构 (JSON Schema)、规则和示例的文本。每次调整 AI 的输出协议或设定，都需要修改这些晦涩的模板文件。

**改造范围：**
1. 废弃 `backend/services/llm/prompts` 下的 `.txt` 模板文件。
2. 在 `backend/services/llm/configs` 目录下创建两个新的 JSON 文件：`parse_goal.json` 和 `generate_graph.json`。
3. 修改 `backend/services/ai_service.py` 的读取逻辑，使其动态解析 JSON 配置文件，并将这些结构化的配置拼装成大模型可理解的 Prompt 文本，并在调用 LLM 接口时注入 JSON 里的 `model_params` (如 `temperature`, `max_tokens`)。

---

## 2. 目录结构变更

```
ConceptTree/backend/services/llm/
├── client.py
├── providers/
├── configs/                  <- 新建目录
│   ├── __init__.py           <- 提供 load_ai_config 辅助函数
│   ├── parse_goal.json       <- 提取自 parse_goal_v1.txt
│   └── generate_graph.json   <- 提取自 generate_graph_v1.txt
└── prompts/                  <- 标记为废弃并删除
    ├── __init__.py
    ├── parse_goal_v1.txt
    └── generate_graph_v1.txt
```

---

## 3. JSON 配置文件结构定义

以 `parse_goal.json` 为例，包含 5 个顶层键：

1.  **`model_params` (Object)**:
    -   `temperature` (Number): 控制生成的随机性（0.0 ~ 1.0）。
    -   `max_tokens` (Number): 限制生成的最大 token 数，防止 JSON 被截断。
2.  **`system_prompt` (String)**:
    -   赋给大模型的角色设定，通常放在 `messages` 数组的 `system` 角色中。
3.  **`output_format` (Object)**:
    -   **核心协议**：以 JSON 的形式定义大模型需要返回的数据结构，属性的值是对该属性的文字描述（而不是具体的值）。
4.  **`rules` (Array of Strings)**:
    -   大模型必须遵守的生成规则或约束。
5.  **`examples` (Array of Objects, 可选)**:
    -   提供给大模型参考的 Few-shot 输入输出示例，每个对象包含 `input` 和 `output` 键。

---

## 4. Prompt 动态组装逻辑 (`configs/__init__.py`)

在组装最终发送给大模型的 `user` message 时，需要将 JSON 的各个部分格式化为易于大模型阅读的文本：

```python
def build_prompt_from_config(config_name: str, user_input: str, **kwargs) -> tuple[dict, str, str]:
    """
    加载配置并构建 Prompt。
    返回: (model_params, system_prompt, user_prompt)
    """
    # 1. 从 configs/{config_name}.json 加载配置数据
    # 2. 提取 model_params (包含可选的 model, temperature, max_tokens) 和 system_prompt
    # 3. 如果 JSON 中存在 system_prompt，允许使用 kwargs 渲染其占位符 (如 {{background}})
    # 4. 组装 user_prompt，例如：
    #    "## Input Format\nUser input: {user_input}\n"
    #    (如果 kwargs 还有没被用在 system_prompt 的数据，可以统一追加到此处)
    #    "## Output Format\nReturn ONLY a JSON object with this exact structure:\n"
    #    json.dumps(config_data["output_format"], indent=2, ensure_ascii=False)
    #    "## Rules\n" + (逐条追加 rules)
    #    "## Examples\n" + (逐条追加 examples)
    #    "Respond ONLY with the JSON object, no markdown formatting, no explanation."
```

---

## 5. `ai_service.py` 的重构

在 `AIService.parse_goal` 和 `AIService.generate_graph` 中：

1.  不再调用 `load_prompt(PARSE_GOAL_V1)`。
2.  调用 `build_prompt_from_config` 函数，传入当前操作的名称和用户输入。
3.  在调用 `self.llm_client.chat_json` 时，将获取到的 `system_prompt`、`user_prompt` 以及 `model_params` 里的 `temperature` 和 `max_tokens` 透传进去。

---

## 6. 验证方案

1.  **静态验证：**
    -   确保 `services/llm/configs/parse_goal.json` 和 `generate_graph.json` 格式合法，没有语法错误。
    -   确保 `services/llm/prompts/` 目录已被删除。
2.  **调用逻辑容错：** `load_ai_config` 找不到文件或解析 JSON 失败时，抛出包含明确错误路径的异常，由上层 `ai_service.py` 捕获并返回 `AI_SERVICE_ERROR` 给前端。
3.  **单元/集成测试：**
    -   运行 `pytest tests/test_ai_integration.py`。
    -   所有 4 个 AI 接口集成测试应当直接通过（因为从外部看，AI 的行为和输出的 Schema 并没有变，仅仅是配置的来源变了）。