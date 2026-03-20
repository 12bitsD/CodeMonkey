"""User background model and clarify-goal endpoint tests.

This module validates Pydantic models and the clarify-goal HTTP endpoint
from two angles:

1. Model-level: UserBackgroundInput defaults, GenerateGraphRequest with
   and without user background, ClarifyGoalRequest validation (including
   rejection of too-short new goals), and ClarifyGoalResponse shape for both
   'modify' and 'create_new' suggestions.

2. Endpoint-level: the clarify-goal API requires auth, rejects short goals,
   and returns a correctly structured response when the AI service is mocked.

These tests exercise model behaviour without database access (no psycopg2
calls), making them fast and suitable for pre-commit validation.

Primary reader: a developer adding new fields to user background models or
debugging validation errors on the clarify-goal request/response models.
"""


def test_user_background_input_defaults():
    """UserBackgroundInput initialises with sensible empty defaults.

    Calling the model with no arguments must produce empty strings and
    empty lists — not None values that would break downstream serialisation.
    Expected: occupation='', abilities=[], masteredKnowledge=[].
    """
    from models import UserBackgroundInput

    bg = UserBackgroundInput()
    assert bg.occupation == ""
    assert bg.abilities == []
    assert bg.masteredKnowledge == []


def test_user_background_input_accepts_lists():
    """UserBackgroundInput accepts and stores non-empty abilities and mastered knowledge lists.

    Expected: abilities has length 2; masteredKnowledge contains '变量'.
    """
    from models import UserBackgroundInput

    bg = UserBackgroundInput(
        abilities=["JavaScript", "Python"], masteredKnowledge=["变量", "循环"]
    )
    assert len(bg.abilities) == 2
    assert "变量" in bg.masteredKnowledge


def test_generate_graph_request_with_user_background():
    """GenerateGraphRequest stores a nested UserBackgroundInput when provided.

    Confirms that passing a populated UserBackgroundInput as userBackground
    is accepted and the abilities are accessible on the resulting model.
    Expected: userBackground is not None, abilities=['JS入门'].
    """
    from routers.ai import GenerateGraphRequest
    from models import UserBackgroundInput

    req = GenerateGraphRequest(
        input="学Python",
        interpretation="掌握Python基础",
        userBackground=UserBackgroundInput(
            abilities=["JS入门"], masteredKnowledge=["变量"]
        ),
    )
    assert req.userBackground is not None
    assert req.userBackground.abilities == ["JS入门"]


def test_generate_graph_request_without_user_background():
    """GenerateGraphRequest allows userBackground to be omitted (defaults to None).

    Not all users fill in their background; the field must be optional.
    Expected: userBackground is None.
    """
    from routers.ai import GenerateGraphRequest

    req = GenerateGraphRequest(input="学Python", interpretation="掌握Python基础")
    assert req.userBackground is None


def test_clarify_goal_request_valid():
    """ClarifyGoalRequest accepts a valid original goal and a sufficiently long new goal.

    Expected: fields are stored as submitted.
    """
    from routers.ai import ClarifyGoalRequest

    req = ClarifyGoalRequest(originalGoal="学Python", newGoal="学Python数据分析")
    assert req.newGoal == "学Python数据分析"
    assert req.originalGoal == "学Python"


def test_clarify_goal_request_new_goal_too_short():
    """ClarifyGoalRequest rejects a new goal that is too short (single character).

    A goal like '学' is not a meaningful learning goal and must fail Pydantic
    validation before reaching any business logic.
    Expected: an exception is raised on construction.
    """
    from routers.ai import ClarifyGoalRequest
    import pytest

    with pytest.raises(Exception):
        ClarifyGoalRequest(originalGoal="学Python", newGoal="学")


def test_clarify_goal_response_model():
    """ClarifyGoalResponse stores a small-change suggestion correctly.

    Creates a response with isLargeChange=False and suggestion='modify',
    representing a minor goal refinement.
    Expected: suggestion='modify', isLargeChange=False.
    """
    from models import ClarifyGoalResponse

    resp = ClarifyGoalResponse(
        interpretation="用Python进行数据分析",
        isLargeChange=False,
        suggestion="modify",
        reason="新目标是原目标的细化方向",
    )
    assert resp.suggestion == "modify"
    assert resp.isLargeChange is False


def test_clarify_goal_response_large_change():
    """ClarifyGoalResponse stores a large-change suggestion correctly.

    Creates a response with isLargeChange=True and suggestion='create_new',
    representing a fundamentally different goal that warrants a new plan.
    Expected: isLargeChange=True, suggestion='create_new'.
    """
    from models import ClarifyGoalResponse

    resp = ClarifyGoalResponse(
        interpretation="使用Java构建后端服务",
        isLargeChange=True,
        suggestion="create_new",
        reason="编程语言完全不同",
    )
    assert resp.isLargeChange is True
    assert resp.suggestion == "create_new"


def test_clarify_goal_endpoint_success(client, auth_headers_a, monkeypatch):
    """The clarify-goal endpoint returns a valid response when the AI service is mocked.

    Monkeypatches AIService.clarify_goal to avoid a real LLM call. Verifies
    that the endpoint correctly forwards the mocked result to the client.
    Expected: HTTP 200, success=True, data.isLargeChange=False, data.suggestion='modify'.
    """
    from services.ai_service import AIService
    from models import ClarifyGoalResponse, ClarifyGoalAIResult

    async def mock_clarify(self, original_goal, new_goal, existing_nodes=None):
        return ClarifyGoalAIResult(
            success=True,
            data=ClarifyGoalResponse(
                interpretation="用Python做数据分析，掌握pandas",
                isLargeChange=False,
                suggestion="modify",
                reason="新目标是原目标的具体化",
            ),
        )

    monkeypatch.setattr(AIService, "clarify_goal", mock_clarify)

    resp = client.post(
        "/api/ai/clarify-goal",
        json={"originalGoal": "学Python", "newGoal": "学Python数据分析"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["isLargeChange"] is False
    assert data["data"]["suggestion"] == "modify"


def test_clarify_goal_endpoint_requires_auth(client):
    """The clarify-goal endpoint rejects unauthenticated requests.

    Expected: HTTP 401.
    """
    resp = client.post(
        "/api/ai/clarify-goal",
        json={"originalGoal": "学Python", "newGoal": "学Python数据分析"},
    )
    assert resp.status_code == 401


def test_clarify_goal_endpoint_validates_short_goal(client, auth_headers_a):
    """The clarify-goal endpoint rejects a new goal that is too short.

    A single-character new goal ('学') must be rejected by the endpoint's
    request validation before the AI service is called.
    Expected: HTTP 400.
    """
    resp = client.post(
        "/api/ai/clarify-goal",
        json={"originalGoal": "学Python", "newGoal": "学"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 400
