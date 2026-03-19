"""
Pydantic request/response schemas for the PathFinder API.

Every API contract type lives in this file, grouped into four sections:

1. **Auth & user** — registration, login, and profile management.
2. **Graph & plan CRUD** — create/read/update plans and their knowledge-graph nodes.
3. **AI service I/O** — structured types consumed and produced by the AI routers.
4. **Shared primitives** — ``NodeStatus``, ``Resource``, ``ApiError``, ``Edge``.

A new developer should pick an existing model or extend one rather than
defining inline ``dict`` types in routers.  ``NodeStatus`` is the single
source of truth for the three learning states a node can be in.
"""

from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from enum import Enum


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


class NodeStatus(str, Enum):
    """The three possible learning states for a knowledge-graph node.

    Inherits from ``str`` so values serialise directly to JSON strings
    without extra configuration.

    Attributes:
        unlearned: The node has not been studied yet (default state).
        learned: The user has marked the node as understood.
        skipped: The user has chosen to bypass this node.
    """

    unlearned = "unlearned"
    learned = "learned"
    skipped = "skipped"


# ---------------------------------------------------------------------------
# Auth and user models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Request body for the user registration endpoint.

    Attributes:
        email: The user's email address, used as the login identifier.
        password: Plain-text password; the backend hashes it before storage.
    """

    email: str
    password: str


class LoginRequest(BaseModel):
    """Request body for the login endpoint.

    Attributes:
        email: Registered email address.
        password: Plain-text password to verify against the stored hash.
    """

    email: str
    password: str


class AuthResponse(BaseModel):
    """Response returned after a successful login or registration.

    Attributes:
        user: Minimal user identity dict (at least ``id`` and ``email``).
        token: A signed JWT the client must send in the ``Authorization`` header.
        expiresIn: Token lifetime in seconds (default: 604 800 = 7 days).
    """

    user: Dict[str, str]
    token: str
    expiresIn: Optional[int] = 604800


class UserProfile(BaseModel):
    """Full user profile used for AI personalisation.

    These fields inform the AI when generating a learning graph, letting it
    tailor node complexity to the user's background.

    Attributes:
        occupation: User's job title or field (optional).
        education: Highest education level (optional).
        programmingLevel: Self-reported programming skill (default: "入门" = beginner).
        mathLevel: Self-reported mathematics skill (default: "入门" = beginner).
        abilities: Free-form list of skills or tools the user already knows.
        masteredKnowledge: Topics the user considers already mastered.
    """

    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = "入门"
    mathLevel: Optional[str] = "入门"
    abilities: List[str] = []
    masteredKnowledge: List[str] = []


class UpdateProfileRequest(BaseModel):
    """Request body for partial profile updates (all fields optional).

    Only fields present in the request body are updated; omitted fields
    retain their current database value.

    Attributes:
        occupation: New occupation string, or ``None`` to leave unchanged.
        education: New education string, or ``None`` to leave unchanged.
        programmingLevel: New programming skill level, or ``None``.
        mathLevel: New mathematics skill level, or ``None``.
        abilities: Replacement list of abilities, or ``None``.
    """

    occupation: Optional[str] = None
    education: Optional[str] = None
    programmingLevel: Optional[str] = None
    mathLevel: Optional[str] = None
    abilities: Optional[List[str]] = None


class BackgroundSummary(BaseModel):
    """A single item in the AI's summary of the user's background.

    The AI produces several of these when interpreting a new learning goal,
    explaining which profile attributes it found relevant.

    Attributes:
        text: Human-readable summary sentence.
        source: Where this item came from (``"profile"`` or ``"input"``).
        isStrength: ``True`` if this item is an advantage for reaching the goal.
    """

    text: str
    source: str
    isStrength: bool


class SplitSuggestion(BaseModel):
    """One alternative sub-goal suggested when a learning goal is too broad.

    Returned by the AI when ``shouldSplit`` is ``True`` in a ``ParseGoalResponse``.

    Attributes:
        title: Short name of the proposed sub-goal.
        description: One-sentence explanation of what the sub-goal covers.
        estimatedNodes: Approximate number of knowledge nodes the sub-goal would generate.
    """

    title: str
    description: str
    estimatedNodes: int


class Resource(BaseModel):
    """An external learning resource linked to a knowledge-graph node.

    Attributes:
        name: Display name of the resource (e.g. "Python Official Docs").
        url: Fully qualified URL to the resource.
        reason: One sentence explaining why this resource is recommended.
    """

    name: str
    url: str
    reason: str


# ---------------------------------------------------------------------------
# Graph & plan CRUD models
# ---------------------------------------------------------------------------


class NodeData(BaseModel):
    """Complete node representation used when creating a plan from AI output.

    Carries the full node payload including rich metadata.  Use ``NodeBase``
    for read responses and ``NodeCreate`` / ``NodeUpdate`` for write operations.

    Attributes:
        id: Stable unique identifier (UUID or AI-generated slug).
        name: Human-readable topic name (e.g. "Linear Algebra Basics").
        status: Current learning state; see ``NodeStatus``.
        x: Horizontal canvas position in pixels.
        y: Vertical canvas position in pixels.
        why: One-sentence rationale for why this node matters to the goal.
        what: Bullet-point list of concepts covered in this node.
        mastery: Criteria the user should meet to consider this node learned.
        prompt: AI-generated study prompt or quiz question for this node.
        resources: Curated external resources for this node.
        isTarget: ``True`` for the single terminal node representing the goal.
        domain: Broad knowledge domain label (e.g. "Mathematics").
    """

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
    """Read-only node representation returned in API responses.

    Identical to ``NodeData`` except ``resources`` are plain dicts (not typed
    ``Resource`` objects) to handle legacy data that may omit the ``reason`` field.

    Attributes:
        id: Stable unique identifier.
        name: Human-readable topic name.
        status: Current learning state.
        x: Horizontal canvas position.
        y: Vertical canvas position.
        why: Rationale for this node's place in the learning path.
        what: Concepts covered.
        mastery: Mastery criteria.
        prompt: AI-generated study prompt.
        resources: List of resource dicts (keys: ``name``, ``url``, ``reason``).
        isTarget: Whether this is the goal node.
    """

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
    """Request payload for inserting a new node into a plan's graph.

    All fields except ``name`` are optional, defaulting to sensible initial
    values for a newly discovered prerequisite node.

    Attributes:
        name: Required topic name.
        status: Initial learning state (default: ``unlearned``).
        x: Initial canvas X position (default: 0).
        y: Initial canvas Y position (default: 0).
        why: Rationale for including this node.
        what: Concepts covered.
        mastery: Mastery criteria.
        prompt: Study prompt.
        resources: Resource dicts.
        is_target: Whether this is the goal node (default: ``False``).
        domain: Knowledge domain label.
    """

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
    """Request payload for partially updating an existing node.

    Only fields that are present and non-``None`` are applied; all others
    retain their current values in the database.

    Attributes:
        status: New learning state.
        x: New canvas X position.
        y: New canvas Y position.
        why: Updated rationale.
        what: Replacement concept list.
        mastery: Replacement mastery list.
        prompt: Replacement study prompt.
        resources: Replacement resource list.
    """

    status: Optional[NodeStatus] = None
    x: Optional[float] = None
    y: Optional[float] = None
    why: Optional[str] = None
    what: Optional[List[str]] = None
    mastery: Optional[List[str]] = None
    prompt: Optional[str] = None
    resources: Optional[List[Dict[str, str]]] = None


class Edge(BaseModel):
    """A directed dependency edge between two knowledge-graph nodes.

    The edge direction encodes prerequisite order: a user should learn
    ``from_node`` before ``to_node``.

    Attributes:
        from_node: ID of the prerequisite node.
        to_node: ID of the node that depends on the prerequisite.
    """

    from_node: str
    to_node: str


class GraphResponse(BaseModel):
    """Complete knowledge graph returned by the graph-fetch endpoint.

    Attributes:
        planId: ID of the plan this graph belongs to.
        title: Human-readable plan title.
        nodes: All nodes in the graph.
        edges: All directed edges encoding prerequisite relationships.
    """

    planId: str
    title: str
    nodes: List[NodeBase]
    edges: List[Edge]


class PlanSummary(BaseModel):
    """Condensed plan metadata used in list views and plan-creation responses.

    Attributes:
        id: Unique plan identifier.
        title: Plan display name.
        progress: Number of nodes marked as ``learned``.
        total: Total number of nodes in the plan.
        status: Plan lifecycle state (e.g. ``"active"``).
        lastAccess: ISO 8601 timestamp of the last time the plan was opened.
        createdAt: ISO 8601 timestamp of plan creation.
    """

    id: str
    title: str
    progress: Optional[int] = 0
    total: Optional[int] = 0
    status: Optional[str] = "active"
    lastAccess: Optional[str] = None
    createdAt: Optional[str] = None


class PlanCreateRequest(BaseModel):
    """Request body for creating a new learning plan from an AI-generated graph.

    Submitted after the user accepts the AI-generated knowledge graph.

    Attributes:
        title: Display name for the plan.
        originalInput: The raw goal text the user typed (preserved for reference).
        nodes: Full node list from the AI response.
        edges: Directed edges from the AI response.
        targetNodeId: ID of the node that represents the ultimate learning goal.
    """

    title: str
    originalInput: str
    nodes: List[NodeData]
    edges: List[Edge]
    targetNodeId: str


class PlanCreateResponse(BaseModel):
    """Response after successfully creating a plan.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Summary of the newly created plan.
    """

    success: bool
    data: PlanSummary


class PlanUpdateRequest(BaseModel):
    """Request body for renaming an existing plan.

    Attributes:
        title: New display name for the plan.
    """

    title: str


class PlanUpdateResponse(BaseModel):
    """Response after successfully updating a plan's metadata.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Arbitrary dict with the updated fields (at minimum ``{"title": ...}``).
    """

    success: bool
    data: Dict[str, Any]


class PlanListResponse(BaseModel):
    """Response for listing all plans belonging to the authenticated user.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: List of plan summaries, ordered by most recent access.
    """

    success: bool
    data: List[PlanSummary]


class GraphApiResponse(BaseModel):
    """Standard API envelope wrapping a ``GraphResponse``.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: The full knowledge graph for the requested plan.
    """

    success: bool
    data: GraphResponse


class ApiError(BaseModel):
    """Machine-readable error detail returned inside an ``ErrorResponse``.

    Attributes:
        code: Short uppercase identifier (e.g. ``"NOT_FOUND"``).
        message: Human-readable error explanation.
    """

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard API error envelope shared by all error responses.

    All error responses from the API share this shape regardless of error
    type, making client-side error handling uniform.

    Attributes:
        success: Always ``False`` for error responses.
        error: Structured error detail.
    """

    success: bool
    error: ApiError


class NodeStatusUpdateRequest(BaseModel):
    """Request body for updating a single node's learning status.

    Attributes:
        status: The new ``NodeStatus`` value to apply.
    """

    status: NodeStatus


class NodePositionUpdateRequest(BaseModel):
    """Request body for updating a node's canvas position after the user drags it.

    Attributes:
        x: New horizontal position in canvas pixels.
        y: New vertical position in canvas pixels.
    """

    x: float
    y: float


class NodeStatusUpdateResponse(BaseModel):
    """Response after successfully updating a node's status.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Dict containing at least the updated ``status`` field.
    """

    success: bool
    data: Dict[str, Any]


class NodePositionUpdateResponse(BaseModel):
    """Response after successfully updating a node's canvas position.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Dict containing the updated ``x`` and ``y`` values.
    """

    success: bool
    data: Dict[str, Any]


class BulkPositionUpdateRequest(BaseModel):
    """Request body for saving multiple node positions in one call.

    Batching position updates reduces round-trips after the user rearranges
    many nodes on the canvas.

    Attributes:
        positions: List of position dicts, each with keys ``id``, ``x``, and ``y``.
    """

    positions: List[Dict[str, Any]]


class BulkPositionUpdateResponse(BaseModel):
    """Response after a bulk position update.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Dict with key ``"updated"`` indicating how many rows were changed.
    """

    success: bool
    data: Dict[str, int]


class AiRecommendRequest(BaseModel):
    """Request body for asking the AI which node to study next.

    Attributes:
        planId: The plan whose current node states should be analysed.
    """

    planId: str


class AiRecommendResponse(BaseModel):
    """Response containing the AI's next-node recommendation.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Dict with at least ``recommended_node_id`` and ``reason``.
    """

    success: bool
    data: Dict[str, Any]


class AiClarifyRequest(BaseModel):
    """Request body for refining an existing learning plan via a follow-up prompt.

    Attributes:
        planId: The plan to refine.
        clarification: The user's natural-language refinement instruction.
    """

    planId: str
    clarification: str


class AiClarifyResponse(BaseModel):
    """Response containing the AI's proposed graph changes after clarification.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Dict describing which nodes to keep, add, and remove.
    """

    success: bool
    data: Dict[str, Any]


class ApplyChangesRequest(BaseModel):
    """Request body for committing AI-proposed graph changes to the database.

    Submitted after the user reviews and accepts the ``AiClarifyResponse``.

    Attributes:
        newGoal: Updated goal description after clarification.
        keep: IDs of existing nodes to retain unchanged.
        add: Full ``NodeCreate`` payloads for nodes to insert.
        remove: IDs of existing nodes to delete.
        newEdges: Complete replacement edge list for the plan.
    """

    newGoal: str
    keep: List[str]
    add: List[NodeCreate]
    remove: List[str]
    newEdges: List[Edge]


class ApplyChangesResponse(BaseModel):
    """Response after applying AI-proposed changes to a plan.

    Attributes:
        success: Always ``True`` when the HTTP status is 200.
        data: Dict summarising the applied changes (added, removed, kept counts).
    """

    success: bool
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# AI response models
# ---------------------------------------------------------------------------
# These types parse and validate the structured JSON returned by the LLM
# before it is forwarded to the client.


class BackgroundItem(BaseModel):
    """One item in the AI's summary of the user's background.

    The AI returns a list of these when parsing a new learning goal,
    explaining which profile attributes influenced its interpretation.

    Attributes:
        text: Human-readable sentence describing the background attribute.
        source: Origin of the data — ``"profile"`` (saved profile) or ``"input"`` (typed goal).
        isStrength: ``True`` if this attribute is advantageous for reaching the goal.
    """

    text: str
    source: str  # "profile" or "input"
    isStrength: bool


class ParseGoalResponse(BaseModel):
    """AI response for the parse-goal endpoint.

    The AI interprets a raw goal string, assesses the user's background,
    and decides whether the goal should be split into smaller sub-goals.

    Attributes:
        interpretation: The AI's paraphrase of the goal in one or two sentences.
        backgroundSummary: Relevant background items the AI considered.
        suggestedNodeCount: Estimated number of knowledge nodes the full graph would have.
        shouldSplit: ``True`` when the goal is too broad for a single graph.
        splitSuggestions: Proposed sub-goals; present only when ``shouldSplit`` is ``True``.
    """

    interpretation: str
    backgroundSummary: List[BackgroundItem]
    suggestedNodeCount: int
    shouldSplit: bool
    splitSuggestions: Optional[List[SplitSuggestion]] = None


class ParseGoalAIResult(BaseModel):
    """Top-level API response wrapper for the parse-goal endpoint.

    Attributes:
        success: ``True`` when the AI returned a valid response.
        data: The parsed goal analysis, present only on success.
        error: Structured error detail, present only on failure.
    """

    success: bool
    data: Optional[ParseGoalResponse] = None
    error: Optional[ApiError] = None


class GraphNode(BaseModel):
    """A knowledge node as returned by the AI graph-generation endpoint.

    Used only for parsing the AI's raw JSON output; the database layer uses
    ``NodeBase`` and ``NodeCreate`` for persistence.

    Attributes:
        id: AI-assigned identifier (slug or UUID).
        name: Topic name (e.g. ``"Gradient Descent"``).
        status: Learning state; always ``"unlearned"`` for newly generated nodes.
        x: Initial canvas X position (default: 0.0).
        y: Initial canvas Y position (default: 0.0).
        why: One-sentence rationale for including this node.
        what: List of concepts this node covers.
        mastery: Criteria defining when the node is considered learned.
        prompt: AI-generated study question or exercise.
        resources: Recommended external resources.
        isTarget: ``True`` for the single terminal node representing the goal.
        domain: Broad knowledge domain (e.g. ``"Mathematics"``).
    """

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
    """A directed dependency edge as returned by the AI graph-generation endpoint.

    Attributes:
        from_node: ID of the prerequisite node (must be learned first).
        to_node: ID of the dependent node.
    """

    from_node: str
    to_node: str


class GenerateGraphResponse(BaseModel):
    """AI response for the generate-graph endpoint.

    Contains the full knowledge graph the AI generated from the user's goal.

    Attributes:
        interpretation: The AI's paraphrase of the goal.
        nodes: All knowledge nodes in the generated graph.
        edges: Directed edges encoding prerequisite order.
        targetNodeId: ID of the node representing the ultimate learning goal.
    """

    interpretation: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    targetNodeId: str


class GenerateGraphAIResult(BaseModel):
    """Top-level API response wrapper for the generate-graph endpoint.

    Attributes:
        success: ``True`` when the AI returned a valid graph.
        data: The generated graph, present only on success.
        error: Structured error detail, present only on failure.
    """

    success: bool
    data: Optional[GenerateGraphResponse] = None
    error: Optional[ApiError] = None


class UserBackgroundInput(BaseModel):
    """User background data bundled into AI prompts for personalisation.

    Collects profile fields and passes them to the LLM so it can tailor
    node difficulty and resource recommendations to the user's level.

    Attributes:
        occupation: User's job or field.
        education: Highest education level.
        programmingLevel: Self-reported programming skill.
        mathLevel: Self-reported mathematics skill.
        abilities: Skills the user already has.
        masteredKnowledge: Topics the user considers already mastered.
    """

    occupation: str = ""
    education: str = ""
    programmingLevel: str = ""
    mathLevel: str = ""
    abilities: List[str] = []
    masteredKnowledge: List[str] = []


class GraphChanges(BaseModel):
    """Proposed node mutations returned by the AI after goal clarification.

    Attributes:
        keep: IDs of existing nodes to leave untouched.
        remove: IDs of existing nodes to delete.
        add: Descriptions of new nodes to insert (plain strings from the AI;
             the frontend converts these to ``NodeCreate`` objects).
    """

    keep: List[str] = []
    remove: List[str] = []
    add: List[str] = []


class ClarifyGoalResponse(BaseModel):
    """AI response after the user submits a follow-up clarification for their goal.

    Attributes:
        interpretation: The AI's updated understanding of the goal.
        isLargeChange: ``True`` when the clarification would restructure most of the graph.
        suggestion: A one-sentence description of the proposed change.
        reason: Explanation of why the AI recommends this change.
        changes: The specific node additions and removals proposed.
    """

    interpretation: str
    isLargeChange: bool
    suggestion: str
    reason: str
    changes: GraphChanges = GraphChanges()


class ClarifyGoalAIResult(BaseModel):
    """Top-level API response wrapper for the clarify-goal endpoint.

    Attributes:
        success: ``True`` when the AI returned a valid clarification.
        data: The clarification response, present only on success.
        error: Structured error detail, present only on failure.
    """

    success: bool
    data: Optional[ClarifyGoalResponse] = None
    error: Optional[ApiError] = None


class RecommendNextResponse(BaseModel):
    """AI response recommending the next node the user should study.

    Attributes:
        recommended_node_id: ID of the suggested node, or ``None`` if all nodes
            are learned or no suitable next step exists.
        reason: One-sentence explanation of the recommendation.
    """

    recommended_node_id: Optional[str] = None
    reason: str


class RecommendNextAIResult(BaseModel):
    """Top-level API response wrapper for the recommend-next endpoint.

    Attributes:
        success: ``True`` when the AI returned a valid recommendation.
        data: The recommendation, present only on success.
        error: Structured error detail, present only on failure.
    """

    success: bool
    data: Optional[RecommendNextResponse] = None
    error: Optional[ApiError] = None
