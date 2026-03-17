def test_user_background_input_defaults():
    from models import UserBackgroundInput

    bg = UserBackgroundInput()
    assert bg.occupation == ""
    assert bg.abilities == []
    assert bg.masteredKnowledge == []


def test_user_background_input_accepts_lists():
    from models import UserBackgroundInput

    bg = UserBackgroundInput(
        abilities=["JavaScript", "Python"], masteredKnowledge=["变量", "循环"]
    )
    assert len(bg.abilities) == 2
    assert "变量" in bg.masteredKnowledge


def test_generate_graph_request_with_user_background():
    from routers.ai import GenerateGraphRequest
    from models import UserBackgroundInput

    req = GenerateGraphRequest(
        input="学Python",
        interpretation="掌握Python基础",
        userBackground=UserBackgroundInput(
            abilities=["JS入门"], masteredKnowledge=["变量"]
        ),
    )
    assert req.userBackground.abilities == ["JS入门"]
    assert req.userBackground is not None


def test_generate_graph_request_without_user_background():
    from routers.ai import GenerateGraphRequest

    req = GenerateGraphRequest(input="学Python", interpretation="掌握Python基础")
    assert req.userBackground is None


def test_clarify_goal_request_valid():
    from routers.ai import ClarifyGoalRequest

    req = ClarifyGoalRequest(originalGoal="学Python", newGoal="学Python数据分析")
    assert req.newGoal == "学Python数据分析"
    assert req.originalGoal == "学Python"


def test_clarify_goal_request_new_goal_too_short():
    from routers.ai import ClarifyGoalRequest
    import pytest

    with pytest.raises(Exception):
        ClarifyGoalRequest(originalGoal="学Python", newGoal="学")


def test_clarify_goal_response_model():
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
    from services.ai_service import AIService
    from models import ClarifyGoalResponse, ClarifyGoalAIResult

    async def mock_clarify(self, original_goal, new_goal):
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
    resp = client.post(
        "/api/ai/clarify-goal",
        json={"originalGoal": "学Python", "newGoal": "学Python数据分析"},
    )
    assert resp.status_code == 401


def test_clarify_goal_endpoint_validates_short_goal(client, auth_headers_a):
    resp = client.post(
        "/api/ai/clarify-goal",
        json={"originalGoal": "学Python", "newGoal": "学"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 422
