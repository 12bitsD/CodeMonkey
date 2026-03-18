# ConceptTree Phase 1 — AI Service Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Replace Mock AI service with real Kimi 2.5 LLM integration for `parse-goal` and `generate-graph` endpoints.

**Architecture:** Adapter pattern LLM client with JSON Schema validation, Prompt templates as files, and fallback error handling.

**Tech Stack:** Python, FastAPI, OpenAI SDK (Kimi 2.5 compatible), Pydantic, Jinja2 for prompts

---

## File Structure

```
ConceptTree/backend/
├── config.py                          # Add LLM config
├── services/
│   ├── ai_service.py                  # Replace Mock implementation
│   └── llm/
│       ├── __init__.py
│       ├── client.py                  # Unified LLM client
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                # Abstract base
│       │   └── openai_compatible.py   # Kimi/OpenAI adapter
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── parse_goal_v1.txt      # parse-goal prompt template
│       │   └── generate_graph_v1.txt  # generate-graph prompt template
│       ├── parser.py                  # JSON response parser
│       └── error_handler.py           # Retry and error handling
├── models.py                          # Add AI response models
└── tests/
    └── test_ai_integration.py         # Integration tests
```

---

## Chunk 1: Configuration and Models

### Task 1.1: Add LLM Configuration to config.py

**Files:**
- Modify: `ConceptTree/backend/config.py`
- Test: Existing config tests

- [ ] **Step 1: Add LLM configuration section**

Add to end of `config.py`:

```python
# LLM Configuration
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "kimi")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.moonshot.cn/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "kimi-k2-5")
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Fallback configuration
LLM_FALLBACK_ENABLED: bool = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
LLM_FALLBACK_PROVIDER: str = os.getenv("LLM_FALLBACK_PROVIDER", "openai")
LLM_FALLBACK_API_KEY: str = os.getenv("LLM_FALLBACK_API_KEY", "")
LLM_FALLBACK_BASE_URL: str = os.getenv("LLM_FALLBACK_BASE_URL", "")
LLM_FALLBACK_MODEL: str = os.getenv("LLM_FALLBACK_MODEL", "gpt-4o-mini")
```

- [ ] **Step 2: Add .env.example entries**

Modify `ConceptTree/backend/.env.example`:

```bash
# LLM Configuration
LLM_PROVIDER=kimi
LLM_API_KEY=your_kimi_api_key_here
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=kimi-k2-5
LLM_TIMEOUT=30
LLM_MAX_RETRIES=3
LLM_TEMPERATURE=0.7

# Fallback LLM (optional)
LLM_FALLBACK_ENABLED=true
LLM_FALLBACK_PROVIDER=openai
LLM_FALLBACK_API_KEY=your_openai_key_here
LLM_FALLBACK_MODEL=gpt-4o-mini
```

- [ ] **Step 3: Verify config loads**

```bash
cd ConceptTree/backend
python -c "from config import Config; print(f'Provider: {Config.LLM_PROVIDER}')"
```

Expected: `Provider: kimi` (or your env value)

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/backend/config.py ConceptTree/backend/.env.example
git commit -m "feat: add LLM configuration for Kimi 2.5 integration"
```

---

### Task 1.2: Add AI Response Models

**Files:**
- Modify: `ConceptTree/backend/models.py`
- Test: Validation tests

- [ ] **Step 1: Add ParseGoal response models**

Add after existing models in `models.py`:

```python
class BackgroundItem(BaseModel):
    """User background summary item"""
    text: str
    source: str  # "profile" or "input"
    isStrength: bool

class SplitSuggestion(BaseModel):
    """Suggested sub-goal when target is too large"""
    title: str
    description: str
    estimatedNodes: int

class ParseGoalResponse(BaseModel):
    """AI response for parse-goal endpoint"""
    interpretation: str
    backgroundSummary: List[BackgroundItem]
    suggestedNodeCount: int
    shouldSplit: bool
    splitSuggestions: Optional[List[SplitSuggestion]] = None

class ParseGoalAIResult(BaseModel):
    """Wrapper for API response"""
    success: bool
    data: Optional[ParseGoalResponse] = None
    error: Optional[ErrorDetail] = None
```

- [ ] **Step 2: Add GenerateGraph response models**

Continue in `models.py`:

```python
class Resource(BaseModel):
    """Learning resource for a node"""
    name: str
    url: Optional[str] = None
    reason: str

class GraphNode(BaseModel):
    """Knowledge node in the graph"""
    id: str
    name: str
    status: str = "unlearned"  # unlearned/learned/skipped
    x: float = 0.0
    y: float = 0.0
    why: str
    what: List[str]
    mastery: List[str]
    prompt: str
    resources: List[Resource] = []
    isTarget: bool = False
    domain: Optional[str] = None

class GraphEdge(BaseModel):
    """Dependency edge between nodes"""
    from_node: str
    to_node: str

class GenerateGraphResponse(BaseModel):
    """AI response for generate-graph endpoint"""
    interpretation: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    targetNodeId: str

class GenerateGraphAIResult(BaseModel):
    """Wrapper for API response"""
    success: bool
    data: Optional[GenerateGraphResponse] = None
    error: Optional[ErrorDetail] = None
```

- [ ] **Step 3: Test model validation**

```python
# Quick validation test
python -c "
from models import ParseGoalResponse, BackgroundItem, GenerateGraphResponse, GraphNode, GraphEdge

# Test ParseGoal
bg = BackgroundItem(text='Python入门', source='profile', isStrength=True)
result = ParseGoalResponse(
    interpretation='理解反向传播',
    backgroundSummary=[bg],
    suggestedNodeCount=7,
    shouldSplit=False
)
print('ParseGoal model OK:', result.interpretation)

# Test GenerateGraph  
node = GraphNode(
    id='n1',
    name='矩阵乘法',
    why='神经网络基础',
    what=['定义', '维度规则'],
    mastery=['手算2x3矩阵'],
    prompt='讲解矩阵乘法'
)
edge = GraphEdge(from_node='n1', to_node='n2')
graph = GenerateGraphResponse(
    interpretation='理解反向传播',
    nodes=[node],
    edges=[edge],
    targetNodeId='n5'
)
print('GenerateGraph model OK:', graph.nodes[0].name)
"
```

Expected:
```
ParseGoal model OK: 理解反向传播
GenerateGraph model OK: 矩阵乘法
```

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/backend/models.py
git commit -m "feat: add AI response Pydantic models for parse-goal and generate-graph"
```

---

## Chunk 2: LLM Client Infrastructure

### Task 2.1: Create LLM Provider Base Class

**Files:**
- Create: `ConceptTree/backend/services/llm/__init__.py`
- Create: `ConceptTree/backend/services/llm/providers/__init__.py`
- Create: `ConceptTree/backend/services/llm/providers/base.py`
- Test: `ConceptTree/backend/tests/test_llm_provider.py`

- [ ] **Step 1: Create provider base class**

Create `ConceptTree/backend/services/llm/providers/base.py`:

```python
"""Abstract base class for LLM providers"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Standardized message format"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardized response format"""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, 
                 model: str = "", timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
    
    @abstractmethod
    async def chat(self, messages: List[LLMMessage], 
                   temperature: float = 0.7,
                   response_format: Optional[Dict] = None) -> LLMResponse:
        """
        Send chat completion request.
        
        Args:
            messages: List of messages
            temperature: Sampling temperature
            response_format: Optional JSON schema for structured output
            
        Returns:
            LLMResponse with content and metadata
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is properly configured and available"""
        pass
```

- [ ] **Step 2: Create OpenAI-compatible adapter**

Create `ConceptTree/backend/services/llm/providers/openai_compatible.py`:

```python
"""OpenAI SDK compatible provider (works with Kimi, OpenAI, etc.)"""
import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI, APIError, Timeout

from .base import BaseLLMProvider, LLMMessage, LLMResponse


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider using OpenAI SDK (compatible with Kimi 2.5)"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None,
                 model: str = "", timeout: int = 30):
        super().__init__(api_key, base_url, model, timeout)
        
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url
            
        self.client = AsyncOpenAI(**client_kwargs)
    
    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key and self.api_key.strip())
    
    async def chat(self, messages: List[LLMMessage],
                   temperature: float = 0.7,
                   response_format: Optional[Dict] = None) -> LLMResponse:
        """
        Send chat completion using OpenAI SDK.
        
        Kimi 2.5 supports response_format={"type": "json_object"}
        """
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Build request kwargs
            request_kwargs = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": temperature,
            }
            
            # Add response_format if provided (for JSON mode)
            if response_format:
                request_kwargs["response_format"] = response_format
            
            response = await self.client.chat.completions.create(**request_kwargs)
            
            return LLMResponse(
                content=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Timeout:
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s")
        except APIError as e:
            raise LLMProviderError(f"API error: {e.message}", status_code=e.status_code)
        except Exception as e:
            raise LLMProviderError(f"Unexpected error: {str(e)}")


class LLMProviderError(Exception):
    """LLM provider specific error"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMTimeoutError(Exception):
    """LLM request timeout"""
    pass
```

- [ ] **Step 3: Create provider __init__.py**

Create `ConceptTree/backend/services/llm/providers/__init__.py`:

```python
"""LLM Providers"""
from .base import BaseLLMProvider, LLMMessage, LLMResponse
from .openai_compatible import OpenAICompatibleProvider, LLMProviderError, LLMTimeoutError

__all__ = [
    'BaseLLMProvider',
    'LLMMessage', 
    'LLMResponse',
    'OpenAICompatibleProvider',
    'LLMProviderError',
    'LLMTimeoutError'
]
```

- [ ] **Step 4: Create llm __init__.py**

Create `ConceptTree/backend/services/llm/__init__.py`:

```python
"""LLM Service Module"""
from .providers import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    OpenAICompatibleProvider,
    LLMProviderError,
    LLMTimeoutError
)

__all__ = [
    'BaseLLMProvider',
    'LLMMessage',
    'LLMResponse', 
    'OpenAICompatibleProvider',
    'LLMProviderError',
    'LLMTimeoutError'
]
```

- [ ] **Step 5: Test provider instantiation**

```bash
cd ConceptTree/backend
python -c "
from services.llm import OpenAICompatibleProvider, LLMMessage

# Test provider creation
provider = OpenAICompatibleProvider(
    api_key='test-key',
    base_url='https://api.moonshot.cn/v1',
    model='kimi-k2-5'
)
print('Provider created:', provider.model)
print('Is available:', provider.is_available())
"
```

Expected:
```
Provider created: kimi-k2-5
Is available: True
```

- [ ] **Step 6: Commit**

```bash
git add ConceptTree/backend/services/llm/
git commit -m "feat: add LLM provider infrastructure with OpenAI-compatible adapter"
```

---

### Task 2.2: Create Unified LLM Client

**Files:**
- Create: `ConceptTree/backend/services/llm/client.py`
- Test: `ConceptTree/backend/tests/test_llm_client.py`

- [ ] **Step 1: Create unified client with retry logic**

Create `ConceptTree/backend/services/llm/client.py`:

```python
"""Unified LLM Client with retry and fallback support"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import Config
from .providers import (
    OpenAICompatibleProvider,
    LLMMessage,
    LLMResponse,
    LLMProviderError,
    LLMTimeoutError
)


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str
    api_key: str
    base_url: Optional[str]
    model: str
    timeout: int
    max_retries: int
    temperature: float


class UnifiedLLMClient:
    """
    Unified client for LLM operations.
    
    Features:
    - Primary provider with fallback
    - Retry logic with exponential backoff
    - JSON mode support
    - Error handling and normalization
    """
    
    def __init__(self):
        self.primary = self._create_primary_provider()
        self.fallback = self._create_fallback_provider() if Config.LLM_FALLBACK_ENABLED else None
        self.max_retries = Config.LLM_MAX_RETRIES
    
    def _create_primary_provider(self) -> OpenAICompatibleProvider:
        """Create primary LLM provider"""
        return OpenAICompatibleProvider(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL if Config.LLM_BASE_URL else None,
            model=Config.LLM_MODEL,
            timeout=Config.LLM_TIMEOUT
        )
    
    def _create_fallback_provider(self) -> Optional[OpenAICompatibleProvider]:
        """Create fallback LLM provider"""
        if not Config.LLM_FALLBACK_API_KEY:
            return None
            
        return OpenAICompatibleProvider(
            api_key=Config.LLM_FALLBACK_API_KEY,
            base_url=Config.LLM_FALLBACK_BASE_URL if Config.LLM_FALLBACK_BASE_URL else None,
            model=Config.LLM_FALLBACK_MODEL,
            timeout=Config.LLM_TIMEOUT
        )
    
    async def chat(self,
                   messages: List[LLMMessage],
                   temperature: Optional[float] = None,
                   response_format: Optional[Dict] = None,
                   use_fallback: bool = False) -> LLMResponse:
        """
        Send chat completion with retry and fallback.
        
        Args:
            messages: List of messages
            temperature: Override default temperature
            response_format: JSON schema for structured output
            use_fallback: Force use of fallback provider
            
        Returns:
            LLMResponse
            
        Raises:
            LLMServiceError: If all retries and fallback exhausted
        """
        provider = self.fallback if use_fallback else self.primary
        
        if not provider or not provider.is_available():
            if use_fallback:
                raise LLMServiceError("Fallback provider not available")
            # Try fallback if primary not available
            if self.fallback and self.fallback.is_available():
                provider = self.fallback
            else:
                raise LLMServiceError("No LLM provider available")
        
        temp = temperature if temperature is not None else Config.LLM_TEMPERATURE
        last_error = None
        
        # Retry loop
        for attempt in range(self.max_retries):
            try:
                response = await provider.chat(
                    messages=messages,
                    temperature=temp,
                    response_format=response_format
                )
                return response
                
            except (LLMTimeoutError, LLMProviderError) as e:
                last_error = e
                # Exponential backoff: 1s, 2s, 4s
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
        
        # All retries exhausted, try fallback if not already using it
        if not use_fallback and self.fallback:
            try:
                return await self.chat(
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                    use_fallback=True
                )
            except Exception as fallback_error:
                # If fallback also fails, raise original error
                pass
        
        raise LLMServiceError(
            f"LLM request failed after {self.max_retries} retries: {str(last_error)}"
        )
    
    async def chat_json(self,
                        system_prompt: str,
                        user_prompt: str,
                        temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Convenience method for JSON mode chat.
        
        Args:
            system_prompt: System message content
            user_prompt: User message content
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON dict
        """
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        response = await self.chat(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        import json
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise LLMServiceError(f"Failed to parse JSON response: {e}")


class LLMServiceError(Exception):
    """Unified LLM service error"""
    pass


# Singleton instance
_llm_client: Optional[UnifiedLLMClient] = None


def get_llm_client() -> UnifiedLLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = UnifiedLLMClient()
    return _llm_client


async def close_llm_client():
    """Close LLM client connections"""
    global _llm_client
    _llm_client = None
```

- [ ] **Step 2: Update llm __init__.py**

Modify `ConceptTree/backend/services/llm/__init__.py`:

```python
"""LLM Service Module"""
from .providers import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    OpenAICompatibleProvider,
    LLMProviderError,
    LLMTimeoutError
)
from .client import UnifiedLLMClient, LLMServiceError, get_llm_client, close_llm_client

__all__ = [
    'BaseLLMProvider',
    'LLMMessage',
    'LLMResponse',
    'OpenAICompatibleProvider',
    'LLMProviderError',
    'LLMTimeoutError',
    'UnifiedLLMClient',
    'LLMServiceError',
    'get_llm_client',
    'close_llm_client'
]
```

- [ ] **Step 3: Test client creation**

```bash
cd ConceptTree/backend
python -c "
from services.llm import get_llm_client, UnifiedLLMClient

# Test singleton
client1 = get_llm_client()
client2 = get_llm_client()
print('Same instance:', client1 is client2)
print('Primary model:', client1.primary.model)
print('Max retries:', client1.max_retries)
"
```

Expected:
```
Same instance: True
Primary model: kimi-k2-5
Max retries: 3
```

- [ ] **Step 4: Commit**

```bash
git add ConceptTree/backend/services/llm/
git commit -m "feat: add unified LLM client with retry and fallback support"
```

---

## Chunk 3: Prompt Templates

### Task 3.1: Create Prompt Templates Directory and Files

**Files:**
- Create: `ConceptTree/backend/services/llm/prompts/__init__.py`
- Create: `ConceptTree/backend/services/llm/prompts/parse_goal_v1.txt`
- Create: `ConceptTree/backend/services/llm/prompts/generate_graph_v1.txt`
- Test: Verify prompt loading

- [ ] **Step 1: Create prompts __init__.py**

Create `ConceptTree/backend/services/llm/prompts/__init__.py`:

```python
"""Prompt templates for LLM operations"""
import os
from pathlib import Path


def load_prompt(name: str) -> str:
    """Load prompt template by name"""
    prompt_dir = Path(__file__).parent
    prompt_file = prompt_dir / f"{name}.txt"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {name}")
    
    return prompt_file.read_text(encoding='utf-8')


# Available prompts
PARSE_GOAL_V1 = "parse_goal_v1"
GENERATE_GRAPH_V1 = "generate_graph_v1"

__all__ = ['load_prompt', 'PARSE_GOAL_V1', 'GENERATE_GRAPH_V1']
```

- [ ] **Step 2: Create parse-goal prompt**

Create `ConceptTree/backend/services/llm/prompts/parse_goal_v1.txt`:

```
You are an AI learning assistant. Parse the user's learning goal and extract structured information.

## Input Format
User input: Their free-form description of what they want to learn and their background

## Output Format
Return ONLY a JSON object with this exact structure:

{
  "interpretation": "Clear, specific learning objective (1 sentence)",
  "backgroundSummary": [
    {
      "text": "Description of strength or weakness",
      "source": "profile" or "input",
      "isStrength": true or false
    }
  ],
  "suggestedNodeCount": number (estimated nodes needed, 3-15),
  "shouldSplit": true or false,
  "splitSuggestions": null or [
    {
      "title": "Specific sub-goal title",
      "description": "What this sub-goal covers",
      "estimatedNodes": number
    }
  ]
}

## Rules
1. interpretation: Make it specific and actionable
2. backgroundSummary: Extract from both explicit statements and implied context
3. suggestedNodeCount: 
   - Simple topic: 3-5 nodes
   - Moderate topic: 6-10 nodes  
   - Complex topic: 11-15 nodes
4. shouldSplit: true if suggestedNodeCount > 12 or goal is very broad
5. splitSuggestions: Provide 2-3 concrete sub-goals if shouldSplit is true

## Examples

Input: "我想学Python"
Output: {
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

Input: "我想理解反向传播，我有Python基础但数学不好"
Output: {
  "interpretation": "理解神经网络反向传播算法的数学原理和代码实现",
  "backgroundSummary": [
    {"text": "Python基础", "source": "input", "isStrength": true},
    {"text": "数学薄弱", "source": "input", "isStrength": false}
  ],
  "suggestedNodeCount": 7,
  "shouldSplit": false,
  "splitSuggestions": null
}

## Current User Input
{{user_input}}

Respond ONLY with the JSON object, no markdown formatting, no explanation.
```

- [ ] **Step 3: Create generate-graph prompt**

Create `ConceptTree/backend/services/llm/prompts/generate_graph_v1.txt`:

```
You are an AI learning assistant. Generate a knowledge dependency graph for the given learning goal.

## Input
- Goal: {{interpretation}}
- Original input: {{original_input}}
- User background: {{background}}

## Output Format
Return ONLY a JSON object with this exact structure:

{
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
}

## Rules

### Node Count
- Generate 5-12 nodes depending on goal complexity
- One node is the TARGET (final goal), others are prerequisites

### Node Fields
1. id: Use n1, n2, n3... format
2. name: Clear, specific concept name in Chinese
3. why: Explain why this matters for the final goal
4. what: 2-4 specific topics/skills to learn
5. mastery: 2-3 concrete, testable criteria
6. prompt: Ready-to-use prompt for an AI tutor
7. resources: 1-2 high-quality resources (can be generic URLs)
8. isTarget: true for exactly ONE node (the final goal)
9. domain: Categorize into 数学基础/编程/机器学习/etc.

### Dependencies (edges)
- Create logical prerequisite chains
- Target node should have at least 2 incoming edges
- Avoid circular dependencies
- Most nodes should have 0-2 outgoing edges

### Layout (x, y coordinates)
- Target node: x=0, y=0 (center)
- Prerequisites: negative y values, spread x from -200 to 200
- Earlier prerequisites: more negative y

### Background Adaptation
If user has strengths/weaknesses:
- Skip very basic nodes if they have strong foundation
- Add foundation nodes if they have weak background
- Adjust mastery criteria based on their level

## Example

Goal: "理解反向传播的数学原理"

Nodes:
1. n1: 导数基础 (prerequisite)
2. n2: 偏导数 (depends on n1)
3. n3: 链式法则 (depends on n2)
4. n4: 梯度下降 (depends on n3)
5. n5: 反向传播 (TARGET, depends on n3, n4)

Edges: n1→n2→n3→n4→n5, n3→n5

Respond ONLY with the JSON object, no markdown formatting, no explanation.
```

- [ ] **Step 4: Test prompt loading**

```bash
cd ConceptTree/backend
python -c "
from services.llm.prompts import load_prompt, PARSE_GOAL_V1, GENERATE_GRAPH_V1

parse_prompt = load_prompt(PARSE_GOAL_V1)
graph_prompt = load_prompt(GENERATE_GRAPH_V1)

print('Parse goal prompt length:', len(parse_prompt))
print('Generate graph prompt length:', len(graph_prompt))
print('Parse contains JSON:', 'JSON' in parse_prompt)
print('Graph contains nodes:', 'nodes' in graph_prompt)
"
```

Expected:
```
Parse goal prompt length: ~1500
Generate graph prompt length: ~2500
Parse contains JSON: True
Graph contains nodes: True
```

- [ ] **Step 5: Commit**

```bash
git add ConceptTree/backend/services/llm/prompts/
git commit -m "feat: add prompt templates for parse-goal and generate-graph"
```

---

## Chunk 4: Replace AI Service Implementation

### Task 4.1: Rewrite ai_service.py with Real LLM Integration

**Files:**
- Modify: `ConceptTree/backend/services/ai_service.py`
- Test: `ConceptTree/backend/tests/test_ai_service.py`

- [ ] **Step 1: Read current ai_service.py**

```bash
cat ConceptTree/backend/services/ai_service.py
```

(Note: Keep the file structure but replace Mock implementations)

- [ ] **Step 2: Rewrite ai_service.py**

Replace `ConceptTree/backend/services/ai_service.py`:

```python
"""AI Service - Real LLM Integration"""
import json
from typing import Optional
from jinja2 import Template

from models import (
    ParseGoalResponse, ParseGoalAIResult,
    GenerateGraphResponse, GenerateGraphAIResult,
    BackgroundItem, SplitSuggestion,
    GraphNode, GraphEdge, Resource,
    ErrorDetail
)
from services.llm import get_llm_client, LLMServiceError
from services.llm.prompts import load_prompt, PARSE_GOAL_V1, GENERATE_GRAPH_V1


class AIService:
    """AI service for learning goal parsing and graph generation"""
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    async def parse_goal(self, user_input: str) -> ParseGoalAIResult:
        """
        Parse user learning goal using LLM.
        
        Args:
            user_input: Raw user input describing what they want to learn
            
        Returns:
            ParseGoalAIResult with structured data or error
        """
        try:
            # Load and render prompt
            prompt_template = load_prompt(PARSE_GOAL_V1)
            prompt = Template(prompt_template).render(user_input=user_input)
            
            # Call LLM
            result = await self.llm_client.chat_json(
                system_prompt="You are a helpful learning assistant.",
                user_prompt=prompt,
                temperature=0.7
            )
            
            # Validate with Pydantic
            parsed = ParseGoalResponse(**result)
            
            return ParseGoalAIResult(
                success=True,
                data=parsed
            )
            
        except LLMServiceError as e:
            return ParseGoalAIResult(
                success=False,
                error=ErrorDetail(
                    code="AI_SERVICE_ERROR",
                    message=f"AI service error: {str(e)}"
                )
            )
        except Exception as e:
            return ParseGoalAIResult(
                success=False,
                error=ErrorDetail(
                    code="AI_SERVICE_ERROR", 
                    message=f"Failed to parse goal: {str(e)}"
                )
            )
    
    async def generate_graph(self, interpretation: str, 
                            original_input: str,
                            user_background: Optional[dict] = None) -> GenerateGraphAIResult:
        """
        Generate knowledge graph using LLM.
        
        Args:
            interpretation: Parsed learning goal
            original_input: Original user input
            user_background: Optional user profile data
            
        Returns:
            GenerateGraphAIResult with graph data or error
        """
        try:
            # Format background for prompt
            background_str = json.dumps(user_background, ensure_ascii=False) if user_background else "无"
            
            # Load and render prompt
            prompt_template = load_prompt(GENERATE_GRAPH_V1)
            prompt = Template(prompt_template).render(
                interpretation=interpretation,
                original_input=original_input,
                background=background_str
            )
            
            # Call LLM
            result = await self.llm_client.chat_json(
                system_prompt="You are a helpful learning assistant.",
                user_prompt=prompt,
                temperature=0.7
            )
            
            # Validate with Pydantic
            parsed = GenerateGraphResponse(**result)
            
            # Validate target node exists
            target_exists = any(node.id == parsed.targetNodeId for node in parsed.nodes)
            if not target_exists:
                return GenerateGraphAIResult(
                    success=False,
                    error=ErrorDetail(
                        code="AI_SERVICE_ERROR",
                        message="Generated graph has invalid target node"
                    )
                )
            
            # Validate edge references
            node_ids = {node.id for node in parsed.nodes}
            for edge in parsed.edges:
                if edge.from_node not in node_ids or edge.to_node not in node_ids:
                    return GenerateGraphAIResult(
                        success=False,
                        error=ErrorDetail(
                            code="AI_SERVICE_ERROR",
                            message="Generated graph has invalid edge references"
                        )
                    )
            
            return GenerateGraphAIResult(
                success=True,
                data=parsed
            )
            
        except LLMServiceError as e:
            return GenerateGraphAIResult(
                success=False,
                error=ErrorDetail(
                    code="AI_SERVICE_ERROR",
                    message=f"AI service error: {str(e)}"
                )
            )
        except Exception as e:
            return GenerateGraphAIResult(
                success=False,
                error=ErrorDetail(
                    code="AI_SERVICE_ERROR",
                    message=f"Failed to generate graph: {str(e)}"
                )
            )


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
```

- [ ] **Step 3: Update ai router to use real service**

Modify `ConceptTree/backend/routers/ai.py` to use the real service (if not already):

```python
"""AI Service Router"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from models import (
    ParseGoalRequest, ParseGoalResponse,
    GenerateGraphRequest, GenerateGraphResponse,
    ErrorResponse
)
from services.ai_service import get_ai_service, AIService
from utils.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/parse-goal", response_model=ParseGoalResponse)
async def parse_goal(
    request: ParseGoalRequest,
    current_user: dict = Depends(get_current_user)
):
    """Parse user learning goal"""
    ai_service = get_ai_service()
    result = await ai_service.parse_goal(request.input)
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error.dict()
        )
    
    return result.data


@router.post("/generate-graph", response_model=GenerateGraphResponse)
async def generate_graph(
    request: GenerateGraphRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate knowledge graph"""
    ai_service = get_ai_service()
    
    # TODO: Load user profile for background context
    user_background = None
    
    result = await ai_service.generate_graph(
        interpretation=request.interpretation,
        original_input=request.input,
        user_background=user_background
    )
    
    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error.dict()
        )
    
    return result.data
```

- [ ] **Step 4: Test AI service integration**

Set your API key first:
```bash
export LLM_API_KEY="your-kimi-api-key"
export LLM_PROVIDER="kimi"
export LLM_MODEL="kimi-k2-5"
```

Run test:
```bash
cd ConceptTree/backend
python -c "
import asyncio
from services.ai_service import get_ai_service

async def test():
    service = get_ai_service()
    
    # Test parse-goal
    result = await service.parse_goal('我想学Python')
    print('Parse result:', result.success)
    if result.success:
        print('Interpretation:', result.data.interpretation)
        print('Node count:', result.data.suggestedNodeCount)
    else:
        print('Error:', result.error.message)

asyncio.run(test())
"
```

Expected: 
```
Parse result: True
Interpretation: 掌握Python编程语言基础
Node count: 8
```

(Or error if API key not set)

- [ ] **Step 5: Commit**

```bash
git add ConceptTree/backend/services/ai_service.py ConceptTree/backend/routers/ai.py
git commit -m "feat: integrate real LLM for parse-goal and generate-graph"
```

---

## Chunk 5: Integration Testing

### Task 5.1: Create Integration Tests

**Files:**
- Create: `ConceptTree/backend/tests/test_ai_integration.py`

- [ ] **Step 1: Write integration tests**

Create `ConceptTree/backend/tests/test_ai_integration.py`:

```python
"""Integration tests for AI service with real LLM"""
import pytest
import os

from services.ai_service import get_ai_service


# Skip tests if no API key configured
pytestmark = pytest.mark.skipif(
    not os.getenv("LLM_API_KEY"),
    reason="LLM_API_KEY not set"
)


@pytest.mark.asyncio
async def test_parse_goal_basic():
    """Test parse-goal with simple input"""
    service = get_ai_service()
    
    result = await service.parse_goal("我想学Python")
    
    assert result.success is True
    assert result.data is not None
    assert "Python" in result.data.interpretation or "python" in result.data.interpretation.lower()
    assert result.data.suggestedNodeCount > 0
    assert result.data.suggestedNodeCount <= 15


@pytest.mark.asyncio
async def test_parse_goal_with_background():
    """Test parse-goal extracts background"""
    service = get_ai_service()
    
    result = await service.parse_goal(
        "我想理解反向传播，我有Python基础但数学不好"
    )
    
    assert result.success is True
    assert result.data is not None
    assert len(result.data.backgroundSummary) >= 2


@pytest.mark.asyncio
async def test_generate_graph_basic():
    """Test generate-graph creates valid graph"""
    service = get_ai_service()
    
    result = await service.generate_graph(
        interpretation="理解Python基础语法",
        original_input="我想学Python",
        user_background=None
    )
    
    assert result.success is True
    assert result.data is not None
    assert len(result.data.nodes) >= 3
    assert len(result.data.nodes) <= 15
    
    # Check target node exists
    target_exists = any(node.id == result.data.targetNodeId 
                       for node in result.data.nodes)
    assert target_exists, "Target node must exist in graph"
    
    # Check edges reference valid nodes
    node_ids = {node.id for node in result.data.nodes}
    for edge in result.data.edges:
        assert edge.from_node in node_ids, f"Edge from {edge.from_node} references non-existent node"
        assert edge.to_node in node_ids, f"Edge to {edge.to_node} references non-existent node"


@pytest.mark.asyncio
async def test_parse_goal_empty_input():
    """Test parse-goal handles edge cases"""
    service = get_ai_service()
    
    result = await service.parse_goal("")
    
    # Should either succeed with generic interpretation or fail gracefully
    if result.success:
        assert result.data is not None
    else:
        assert result.error is not None
```

- [ ] **Step 2: Run integration tests**

```bash
cd ConceptTree/backend
export LLM_API_KEY="your-key"
python -m pytest tests/test_ai_integration.py -v
```

Expected: All tests pass (or skip if no API key)

- [ ] **Step 3: Commit**

```bash
git add ConceptTree/backend/tests/test_ai_integration.py
git commit -m "test: add AI service integration tests"
```

---

## Phase 1 Completion Checklist

- [ ] Config: LLM settings added
- [ ] Models: ParseGoalResponse, GenerateGraphResponse added
- [ ] LLM Client: Unified client with retry/fallback
- [ ] Prompts: parse_goal_v1.txt, generate_graph_v1.txt
- [ ] Service: ai_service.py uses real LLM
- [ ] Router: ai.py calls real service
- [ ] Tests: Integration tests pass

**Exit Criteria**:
- `POST /api/ai/parse-goal` returns real AI-parsed data
- `POST /api/ai/generate-graph` returns real knowledge graph
- All tests pass with valid API key

---

*Plan Version*: 1.0  
*Created*: 2025-03-17
