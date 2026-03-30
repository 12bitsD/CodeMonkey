# Epic 2: 图谱核心

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
from enum import Enum


class NodeStatus(str, Enum):
    unlearned = "unlearned"
    learned = "learned"
    skipped = "skipped"


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


class PlanCreateResponse(BaseModel):
    success: bool
    data: PlanSummary


class PlanUpdateRequest(BaseModel):
    title: str


class PlanUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, object]


class PlanListResponse(BaseModel):
    success: bool
    data: List[PlanSummary]


class GraphApiResponse(BaseModel):
    success: bool
    data: GraphResponse


class NodeStatusUpdateRequest(BaseModel):
    status: NodeStatus


class NodePositionUpdateRequest(BaseModel):
    x: float
    y: float


class NodeStatusUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, object]


class NodePositionUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, object]


class BulkPositionUpdateRequest(BaseModel):
    positions: List[Dict[str, object]]


class BulkPositionUpdateResponse(BaseModel):
    success: bool
    data: Dict[str, int]
