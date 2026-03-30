from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, TYPE_CHECKING


class ApiError(BaseModel):
    code: str
    message: str


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


class BackgroundItem(BaseModel):
    text: str
    source: str
    isStrength: bool


class ParseGoalResponse(BaseModel):
    interpretation: str
    backgroundSummary: List[BackgroundItem]
    suggestedNodeCount: int
    shouldSplit: bool
    splitSuggestions: Optional[List[SplitSuggestion]] = None


class ParseGoalAIResult(BaseModel):
    success: bool
    data: Optional[ParseGoalResponse] = None
    error: Optional[ApiError] = None


class GraphNode(BaseModel):
    id: str
    name: str
    status: str = "unlearned"
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
    from_node: str
    to_node: str


class GenerateGraphResponse(BaseModel):
    interpretation: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    targetNodeId: str


class GenerateGraphAIResult(BaseModel):
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


class AiRecommendRequest(BaseModel):
    planId: str


class AiClarifyRequest(BaseModel):
    planId: str
    clarification: str


class ApplyChangesRequest(BaseModel):
    newGoal: str
    keep: List[str]
    add: List
    remove: List[str]
    newEdges: List


class ApplyChangesResponse(BaseModel):
    success: bool
    data: dict


class ErrorResponse(BaseModel):
    success: bool
    error: ApiError
