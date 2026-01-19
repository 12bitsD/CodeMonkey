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
