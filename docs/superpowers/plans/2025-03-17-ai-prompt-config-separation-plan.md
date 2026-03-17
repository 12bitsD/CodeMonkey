# AI Prompt Configuration Separation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Move AI prompt text, rules, JSON formats, and model parameters from code/jinja to standalone JSON files.

**Architecture:** 
- JSON config files in `configs/`
- Dynamic assembly using a helper function in `configs/__init__.py`
- Minimal changes in `ai_service.py` to route logic

**Tech Stack:** Python, JSON

---

## Chunk 1: Setup JSON Configurations

### Task 1.1: Create Configuration Files

**Files:**
- Delete: `ConceptTree/backend/services/llm/prompts/parse_goal_v1.txt`
- Delete: `ConceptTree/backend/services/llm/prompts/generate_graph_v1.txt`
- Delete: `ConceptTree/backend/services/llm/prompts/__init__.py`
- Create: `ConceptTree/backend/services/llm/configs/parse_goal.json`
- Create: `ConceptTree/backend/services/llm/configs/generate_graph.json`

- [ ] **Step 1: Create `parse_goal.json`**
```bash
mkdir -p ConceptTree/backend/services/llm/configs
```
Create `ConceptTree/backend/services/llm/configs/parse_goal.json`:
```json
{
  "model_params": {
    "temperature": 0.7,
    "max_tokens": 1500
  },
  "system_prompt": "You are an AI learning assistant. Parse the user's learning goal and extract structured information.",
  "output_format": {
    "interpretation": "Clear, specific learning objective (1 sentence)",
    "backgroundSummary": [
      {
        "text": "Description of strength or weakness",
        "source": "profile or input",
        "isStrength": "true or false (boolean)"
      }
    ],
    "suggestedNodeCount": "number (estimated nodes needed, 3-15)",
    "shouldSplit": "true or false (boolean)",
    "splitSuggestions": [
      {
        "title": "Specific sub-goal title",
        "description": "What this sub-goal covers",
        "estimatedNodes": "number"
      }
    ]
  },
  "rules": [
    "interpretation: Make it specific and actionable",
    "backgroundSummary: Extract from both explicit statements and implied context",
    "suggestedNodeCount: Simple topic 3-5 nodes, Moderate topic 6-10 nodes, Complex topic 11-15 nodes",
    "shouldSplit: true if suggestedNodeCount > 12 or goal is very broad",
    "splitSuggestions: Provide 2-3 concrete sub-goals if shouldSplit is true"
  ],
  "examples": [
    {
      "input": "我想学Python",
      "output": {
        "interpretation": "掌握Python编程语言基础",
        "backgroundSummary": [],
        "suggestedNodeCount": 8,
        "shouldSplit": true,
        "splitSuggestions": [
          {"title": "Python基础语法", "description": "变量、数据类型、控制流", "estimatedNodes": 5},
          {"title": "Python函数与模块", "description": "函数定义、模块导入、标准库", "estimatedNodes": 4},
          {"title": "Python面向对象编程", "description": "类、对象、继承、封装", "estimatedNodes": 5}
        ]
      }
    },
    {
      "input": "我想理解反向传播，我有Python基础但数学不好",
      "output": {
        "interpretation": "理解神经网络反向传播算法的数学原理和代码实现",
        "backgroundSummary": [
          {"text": "Python基础", "source": "input", "isStrength": true},
          {"text": "数学薄弱", "source": "input", "isStrength": false}
        ],
        "suggestedNodeCount": 7,
        "shouldSplit": false,
        "splitSuggestions": null
      }
    }
  ]
}
```

- [ ] **Step 2: Create `generate_graph.json`**
Create `ConceptTree/backend/services/llm/configs/generate_graph.json`:
```json
{
  "model_params": {
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "system_prompt": "You are an AI learning assistant. Generate a knowledge dependency graph for the given learning goal.",
  "output_format": {
    "interpretation": "The learning goal (echo back)",
    "nodes": [
      {
        "id": "n1",
        "name": "Node name in Chinese",
        "status": "unlearned",
        "x": 0.0,
        "y": 0.0,
        "why": "Why learn this - connection to the goal (2-3 sentences)",
        "what": ["Specific topic 1", "Specific topic 2", "Specific topic 3"],
        "mastery": ["Actionable check 1", "Actionable check 2"],
        "prompt": "Prompt to ask an AI tutor about this topic",
        "resources": [
          {"name": "Resource name", "url": "optional url", "reason": "Why this resource"}
        ],
        "isTarget": false,
        "domain": "领域分类如: 数学基础/编程/机器学习"
      }
    ],
    "edges": [
      {"from_node": "n1", "to_node": "n2"}
    ],
    "targetNodeId": "id of the target node"
  },
  "rules": [
    "Node Count: Generate 5-12 nodes depending on goal complexity",
    "Node Fields: id MUST be n1, n2 format. name MUST be Chinese. isTarget MUST be true for exactly ONE node.",
    "Dependencies (edges): Create logical prerequisite chains. Target node should have at least 2 incoming edges. Avoid circular dependencies.",
    "Layout: Target node x=0, y=0. Prerequisites negative y values, spread x from -200 to 200.",
    "Background Adaptation: If user has strengths, skip basic nodes. If weaknesses, add foundation nodes."
  ],
  "examples": [
    {
      "input": "理解反向传播的数学原理",
      "output": "Nodes: 导数基础, 偏导数, 链式法则, 梯度下降, 反向传播. Edges: 导数基础->偏导数, 偏导数->链式法则, 链式法则->反向传播, 链式法则->梯度下降, 梯度下降->反向传播"
    }
  ]
}
```

- [ ] **Step 3: Delete old prompt files**
```bash
cd ConceptTree/backend/services/llm
rm -rf prompts/
```

- [ ] **Step 4: Commit**
```bash
git add ConceptTree/backend/services/llm/configs/
git rm -rf ConceptTree/backend/services/llm/prompts/
git commit -m "refactor(llm): move text prompts to JSON configurations"
```

---

## Chunk 2: Configuration Loader

### Task 2.1: Build `load_ai_config` utility

**Files:**
- Create: `ConceptTree/backend/services/llm/configs/__init__.py`

- [ ] **Step 1: Write configuration loader and assembler**
Create `ConceptTree/backend/services/llm/configs/__init__.py`:
```python
import json
from pathlib import Path
from typing import Dict, Tuple, Any

class ConfigLoadError(Exception):
    pass

def load_ai_config(config_name: str, user_input: str, **kwargs) -> Tuple[Dict[str, Any], str, str]:
    """
    Load AI configuration from JSON and assemble the final prompts.
    
    Returns:
        (model_params, system_prompt, user_prompt)
    """
    config_dir = Path(__file__).parent
    config_file = config_dir / f"{config_name}.json"
    
    if not config_file.exists():
        raise ConfigLoadError(f"Configuration file not found: {config_file}")
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in {config_file}: {str(e)}")
        
    model_params = config.get("model_params", {})
    system_prompt = config.get("system_prompt", "You are a helpful AI assistant.")
    
    # 3. Allow placeholder rendering in system_prompt
    for k, v in kwargs.items():
        placeholder = f"{{{{{k}}}}}"
        if placeholder in system_prompt:
            system_prompt = system_prompt.replace(placeholder, str(v))
            
    # Assembly User Prompt
    parts = []
    parts.append("## Input")
    parts.append(f"User input: {user_input}")
    
    # Append any dynamic kwargs that weren't used in system_prompt
    for k, v in kwargs.items():
        if f"{{{{{k}}}}}" not in config.get("system_prompt", ""):
            parts.append(f"{k}: {v}")
        
    if "output_format" in config:
        parts.append("\n## Output Format")
        parts.append("Return ONLY a JSON object with this exact structure:")
        parts.append(json.dumps(config["output_format"], indent=2, ensure_ascii=False))
        
    if "rules" in config and config["rules"]:
        parts.append("\n## Rules")
        for rule in config["rules"]:
            parts.append(f"- {rule}")
            
    if "examples" in config and config["examples"]:
        parts.append("\n## Examples")
        for ex in config["examples"]:
            parts.append(f"Input: {ex.get('input', '')}")
            if "output" in ex:
                parts.append(f"Output: {json.dumps(ex['output'], ensure_ascii=False)}")
            parts.append("")
            
    parts.append("\nRespond ONLY with the JSON object, no markdown formatting, no explanation.")
    
    user_prompt = "\n".join(parts)
    
    return model_params, system_prompt, user_prompt
```

- [ ] **Step 2: Test the loader**
```bash
cd ConceptTree/backend
python -c "
from services.llm.configs import load_ai_config
params, sys_p, usr_p = load_ai_config('parse_goal', '我想学JS')
print('Params:', params)
print('System:', sys_p)
print('User prompt contains JSON schema:', 'interpretation' in usr_p)
print('User prompt contains input:', '我想学JS' in usr_p)
"
```
Expected: All output confirms proper loading.

- [ ] **Step 3: Commit**
```bash
git add ConceptTree/backend/services/llm/configs/__init__.py
git commit -m "feat(llm): add prompt builder utility for JSON configurations"
```

---

## Chunk 3: AI Service Integration

### Task 3.1: Refactor `ai_service.py` to use new configs

**Files:**
- Modify: `ConceptTree/backend/services/ai_service.py`

- [ ] **Step 1: Replace prompt loading logic**
Modify `ConceptTree/backend/services/ai_service.py`:
- Remove `jinja2` imports
- Remove imports from `.prompts`
- Import `load_ai_config` and `ConfigLoadError` from `.configs`

```python
import json
from typing import Optional

from models import (
    ParseGoalResponse, ParseGoalAIResult,
    GenerateGraphResponse, GenerateGraphAIResult,
    ApiError
)
from services.llm import get_llm_client, LLMServiceError
from services.llm.configs import load_ai_config, ConfigLoadError

class AIService:
    def __init__(self):
        self.llm_client = get_llm_client()

    async def parse_goal(self, user_input: str) -> ParseGoalAIResult:
        try:
            params, sys_prompt, usr_prompt = load_ai_config("parse_goal", user_input)
            
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 4096)
            )
            
            parsed = ParseGoalResponse(**result)
            return ParseGoalAIResult(success=True, data=parsed)
            
        except (LLMServiceError, ConfigLoadError) as e:
            return ParseGoalAIResult(
                success=False,
                error=ApiError(code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}")
            )
        except Exception as e:
            return ParseGoalAIResult(
                success=False,
                error=ApiError(code="AI_SERVICE_ERROR", message=f"Failed to parse goal: {str(e)}")
            )

    async def generate_graph(self, interpretation: str, 
                            original_input: str,
                            user_background: Optional[dict] = None) -> GenerateGraphAIResult:
        try:
            background_str = json.dumps(user_background, ensure_ascii=False) if user_background else "无"
            
            params, sys_prompt, usr_prompt = load_ai_config(
                "generate_graph", 
                interpretation, 
                original_input=original_input, 
                background=background_str
            )
            
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 4096)
            )
            
            parsed = GenerateGraphResponse(**result)
            
            target_exists = any(node.id == parsed.targetNodeId for node in parsed.nodes)
            if not target_exists:
                return GenerateGraphAIResult(
                    success=False,
                    error=ApiError(code="AI_SERVICE_ERROR", message="Generated graph has invalid target node")
                )
            
            node_ids = {node.id for node in parsed.nodes}
            for edge in parsed.edges:
                if edge.from_node not in node_ids or edge.to_node not in node_ids:
                    return GenerateGraphAIResult(
                        success=False,
                        error=ApiError(code="AI_SERVICE_ERROR", message="Generated graph has invalid edge references")
                    )
            
            return GenerateGraphAIResult(success=True, data=parsed)
            
        except (LLMServiceError, ConfigLoadError) as e:
            return GenerateGraphAIResult(
                success=False,
                error=ApiError(code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}")
            )
        except Exception as e:
            return GenerateGraphAIResult(
                success=False,
                error=ApiError(code="AI_SERVICE_ERROR", message=f"Failed to generate graph: {str(e)}")
            )

_ai_service: Optional[AIService] = None

def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
```

- [ ] **Step 2: Run Integration Tests**
```bash
cd ConceptTree/backend
python -m pytest tests/test_ai_integration.py -v --noconftest
```
Expected: Tests should skip (if no key) or PASS. No code failures.

- [ ] **Step 3: Commit**
```bash
git add ConceptTree/backend/services/ai_service.py ConceptTree/backend/services/llm/configs/
git commit -m "refactor(ai): rewrite AI Service to load prompts from dynamic JSON configs"
```

## Final Review
Review implementation and ensure everything functions without `.txt` template dependencies.
