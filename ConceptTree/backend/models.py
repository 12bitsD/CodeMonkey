from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeStatus(str, Enum):
    unlearned = "unlearned"
    learned = "learned"
    skipped = "skipped"


class LearningPurpose(str, Enum):
    explore = "explore"   # 了解这个领域 → 认知层+理解层（depth 1-2）
    apply   = "apply"     # 项目/工作中能用 → 认知+理解+应用层（depth 1-3）
    master  = "master"    # 系统精通 → 全4层（含内化/自测）


# ========== 认证和用户相关模型 ==========


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user: Dict[str, str]
    token: str
    expiresIn: Optional[int] = 604800


class UserProfile(BaseModel):
    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = "入门"
    mathLevel: Optional[str] = "入门"
    abilities: List[str] = []
    masteredKnowledge: List[str] = []


class UpdateProfileRequest(BaseModel):
    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = None
    mathLevel: Optional[str] = None
    abilities: Optional[List[str]] = None


class BackgroundSummary(BaseModel):
    text: str
    source: str
    isStrength: bool


class SplitSuggestion(BaseModel):
    title: str
    description: str
    estimatedNodes: int


class Resource(BaseModel):
    name: str
    url: Optional[str] = ""
    reason: str


class ResourceSearchCache(BaseModel):
    items: List[Dict[str, str]] = []
    query: Optional[str] = None
    updatedAt: Optional[str] = None


class NodeData(BaseModel):
    id: str
    name: str
    status: NodeStatus
    x: float
    y: float
    why: Optional[str] = None
    what: List[str] = []
    mastery: List[str] = []
    prompt: Optional[str] = None
    resources: List[Resource] = []
    contentCache: Dict[str, str] = {}
    resourceSearchCache: Dict[str, Any] = {}
    isTarget: bool = False
    domain: Optional[str] = None
    phase: Optional[str] = None
    phase_order: int = 0
    depth_level: int = 2


class NodeBase(BaseModel):
    id: str
    name: str
    status: NodeStatus
    x: float
    y: float
    why: Optional[str] = None
    what: List[str] = []
    mastery: List[str] = []
    prompt: Optional[str] = None
    resources: List[Dict[str, str]] = []
    contentCache: Dict[str, str] = {}
    resourceSearchCache: Dict[str, Any] = {}
    isTarget: bool = False
    phase: Optional[str] = None
    phase_order: int = 0
    depth_level: int = 2


class NodeCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    status: NodeStatus = NodeStatus.unlearned
    x: float = 0
    y: float = 0
    why: Optional[str] = None
    what: List[str] = []
    mastery: List[str] = []
    prompt: Optional[str] = None
    resources: List[Dict[str, str]] = []
    is_target: bool = Field(False, alias="isTarget")
    domain: Optional[str] = None


class NodeUpdate(BaseModel):
    status: Optional[NodeStatus] = None
    x: Optional[float] = None
    y: Optional[float] = None
    why: Optional[str] = None
    what: Optional[List[str]] = None
    mastery: Optional[List[str]] = None
    prompt: Optional[str] = None
    resources: Optional[List[Dict[str, str]]] = None


class Edge(BaseModel):
    from_node: str
    to_node: str


class GraphResponse(BaseModel):
    planId: str
    title: str
    nodes: List[NodeBase]
    edges: List[Edge]


class PlanSummary(BaseModel):
    id: str
    title: str
    progress: Optional[int] = 0
    total: Optional[int] = 0
    status: Optional[str] = "active"
    lastAccess: Optional[str] = None
    createdAt: Optional[str] = None


class PlanCreateRequest(BaseModel):
    title: str
    originalInput: str
    nodes: List[NodeData]
    edges: List[Edge]
    targetNodeId: str
    learning_purpose: str = "apply"  # F1: explore / apply / master


class PlanCreateResponse(BaseModel):
    success: bool
    data: PlanSummary


class PlanUpdateRequest(BaseModel):
    title: str


class PlanUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class PlanListResponse(BaseModel):
    success: bool
    data: List[PlanSummary]


class GraphApiResponse(BaseModel):
    success: bool
    data: GraphResponse


class ResourceSearchRequest(BaseModel):
    query: Optional[str] = None


class ResourceSearchResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class ApiError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool
    error: ApiError


class NodeStatusUpdateRequest(BaseModel):
    status: NodeStatus


class NodePositionUpdateRequest(BaseModel):
    x: float
    y: float


class NodeStatusUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class NodePositionUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class BulkPositionUpdateRequest(BaseModel):
    positions: List[Dict[str, Any]]


class BulkPositionUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, int]


class AiRecommendRequest(BaseModel):
    planId: str


class AiRecommendResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class AiClarifyRequest(BaseModel):
    planId: str
    clarification: str


class AiClarifyResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


class ApplyChangesResponse(BaseModel):
    success: bool
    data: Dict[str, Any]


# ========== AI 响应模型 ==========


class BackgroundItem(BaseModel):
    """User background summary item"""

    text: str
    source: str  # "profile" or "input"
    isStrength: bool


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
    error: Optional[ApiError] = None


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
    # F3 — 阶段分组字段
    phase: Optional[str] = None        # 地基 / 核心 / 应用 / 进阶
    phase_order: int = 0               # 阶段排序
    depth_level: int = 2               # 内容深度（由 learning_purpose 决定）


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
    error: Optional[ApiError] = None


class UserBackgroundInput(BaseModel):
    occupation: str = ""
    education: str = ""
    programmingLevel: str = ""
    mathLevel: str = ""
    abilities: List[str] = []
    masteredKnowledge: List[str] = []


class GraphChanges(BaseModel):
    keep: List[str] = []
    remove: List[str] = []
    add: List[str] = []


class ClarifyGoalResponse(BaseModel):
    interpretation: str
    isLargeChange: bool
    suggestion: str
    reason: str
    changes: GraphChanges = GraphChanges()


class ClarifyGoalAIResult(BaseModel):
    success: bool
    data: Optional[ClarifyGoalResponse] = None
    error: Optional[ApiError] = None


class RecommendNextResponse(BaseModel):
    recommendedNodeId: Optional[str] = Field(default=None, alias="recommended_node_id")
    reason: str

    model_config = ConfigDict(populate_by_name=True)


class RecommendNextAIResult(BaseModel):
    success: bool
    data: Optional[RecommendNextResponse] = None
    error: Optional[ApiError] = None


# ========== Sprint 3: AI Deep Content + Chat 模型 ==========


class NodeContextInput(BaseModel):
    """节点学习上下文（用于 explain-topic 和 chat）"""
    nodeName: str
    why: Optional[str] = None
    planTitle: Optional[str] = None


class ExplainTopicRequest(BaseModel):
    """F7: 解释 what 列表中的某个主题"""
    nodeId: str
    topicIndex: int
    topicText: str
    nodeContext: NodeContextInput


class ChatMessage(BaseModel):
    """单条聊天消息"""
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """F4: 节点聊天请求"""
    messages: List[ChatMessage]
    nodeContext: Optional[NodeContextInput] = None
    enableWebSearch: bool = False
