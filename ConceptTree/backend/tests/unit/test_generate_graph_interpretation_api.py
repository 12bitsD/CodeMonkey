from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.ai as ai_router
from models import GenerateGraphAIResult, GenerateGraphResponse, GraphNode


def test_generate_graph_route_uses_interpretation_field(monkeypatch):
    captured = {}

    class FakeAIService:
        async def generate_graph(
            self, interpretation, original_input, user_background=None
        ):
            captured["interpretation"] = interpretation
            captured["original_input"] = original_input
            captured["user_background"] = user_background
            return GenerateGraphAIResult(
                success=True,
                data=GenerateGraphResponse(
                    interpretation=interpretation,
                    nodes=[
                        GraphNode(
                            id="n_target",
                            name="目标节点",
                            why="说明原因",
                            what=["知识点"],
                            mastery=["掌握标准"],
                            prompt="学习提示",
                            isTarget=True,
                        )
                    ],
                    edges=[],
                    targetNodeId="n_target",
                ),
            )

    app = FastAPI()
    app.include_router(ai_router.router)
    app.dependency_overrides[ai_router.get_current_user_id] = lambda: "u_test"
    app.dependency_overrides[ai_router.get_db] = lambda: None
    monkeypatch.setattr(ai_router, "get_ai_service", lambda: FakeAIService())

    with TestClient(app) as client:
        response = client.post(
            "/api/ai/generate-graph",
            json={
                "input": "我想理解深度学习中的反向传播，我有Python基础但数学不好",
                "interpretation": "理解深度学习中的反向传播",
            },
        )

    assert response.status_code == 200
    assert captured == {
        "interpretation": "理解深度学习中的反向传播",
        "original_input": "我想理解深度学习中的反向传播，我有Python基础但数学不好",
        "user_background": None,
    }
    assert response.json()["data"]["interpretation"] == "理解深度学习中的反向传播"
