from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum

from epic_1.models import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserProfile,
    UpdateProfileRequest,
)
from epic_2.models import (
    NodeStatus,
    Resource,
    NodeData,
    NodeBase,
    NodeCreate,
    NodeUpdate,
    Edge,
    GraphResponse,
    PlanSummary,
    PlanCreateRequest,
    PlanCreateResponse,
    PlanUpdateRequest,
    PlanUpdateResponse,
    PlanListResponse,
    GraphApiResponse,
    NodeStatusUpdateRequest,
    NodePositionUpdateRequest,
    NodeStatusUpdateResponse,
    NodePositionUpdateResponse,
    BulkPositionUpdateRequest,
    BulkPositionUpdateResponse,
)
from epic_3.models import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    NoteListResponse,
)
from epic_4.models import (
    BackgroundSummary,
    SplitSuggestion,
    BackgroundItem,
    ParseGoalResponse,
    ParseGoalAIResult,
    GraphNode,
    GraphEdge,
    GenerateGraphResponse,
    GenerateGraphAIResult,
    UserBackgroundInput,
    GraphChanges,
    ClarifyGoalResponse,
    ClarifyGoalAIResult,
    RecommendNextResponse,
    RecommendNextAIResult,
    AiRecommendRequest,
    AiClarifyRequest,
    ApplyChangesRequest,
    ApplyChangesResponse,
    ApiError,
    ErrorResponse,
)
from epic_5.models import (
    StatsOverview,
    DomainDistribution,
    StatsDistribution,
)
