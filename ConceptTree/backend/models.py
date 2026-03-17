from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from enum import Enum


class NodeStatus(str, Enum):
    unlearned = "unlearned"
    learned = "learned"
    skipped = "skipped"


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
    url: str
    reason: str


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
    isTarget: bool = False
    domain: Optional[str] = None


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
    isTarget: bool = False


class NodeCreate(BaseModel):
    name: str
    status: NodeStatus = NodeStatus.unlearned
    x: float = 0
    y: float = 0
    why: Optional[str] = None
    what: List[str] = []
    mastery: List[str] = []
    prompt: Optional[str] = None
    resources: List[Dict[str, str]] = []
    is_target: bool = False
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


class ApplyChangesRequest(BaseModel):
    newGoal: str
    keep: List[str]
    add: List[NodeCreate]
    remove: List[str]
    newEdges: List[Edge]


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
    recommended_node_id: Optional[str] = None
    reason: str


class RecommendNextAIResult(BaseModel):
    success: bool
    data: Optional[RecommendNextResponse] = None
    error: Optional[ApiError] = None
