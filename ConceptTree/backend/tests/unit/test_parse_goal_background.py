import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import UserBackgroundInput
from routers.ai import ParseGoalRequest
from services.ai_service import AIService


@pytest.mark.asyncio
async def test_parse_goal_request_and_service_pass_user_background():
    user_background = {
        "occupation": "产品经理",
        "education": "本科",
        "programmingLevel": "入门",
        "mathLevel": "中等",
        "abilities": ["Python基础"],
        "masteredKnowledge": ["变量", "循环"],
    }
    captured = {}

    def mock_load_ai_config(config_name, user_input, **kwargs):
        captured["config_name"] = config_name
        captured["user_input"] = user_input
        captured["background"] = kwargs.get("background")
        return ({}, "system prompt", "user prompt")

    request = ParseGoalRequest(
        input="我想学反向传播",
        userBackground=UserBackgroundInput(**user_background),
    )

    with patch("services.ai_service.load_ai_config", side_effect=mock_load_ai_config):
        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(
                return_value={
                    "interpretation": "理解反向传播",
                    "backgroundSummary": [],
                    "suggestedNodeCount": 5,
                    "shouldSplit": False,
                }
            )
            mock_get_client.return_value = mock_client

            request_user_background = getattr(request, "userBackground", None)
            assert request_user_background is not None

            service = AIService()
            result = await service.parse_goal(
                request.input,
                user_background=request_user_background.model_dump(),
            )

    assert result.success is True
    assert captured["config_name"] == "parse_goal"
    assert captured["user_input"] == "我想学反向传播"
    assert captured["background"] == json.dumps(user_background, ensure_ascii=False)


@pytest.mark.asyncio
async def test_parse_goal_compacts_generated_plan_title():
    with patch("services.ai_service.load_ai_config", return_value=({}, "system", "user")):
        with patch("services.ai_service.get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_json = AsyncMock(
                return_value={
                    "title": "Understand the mathematical foundations of backpropagation in neural networks",
                    "interpretation": "Understand how backpropagation trains a neural network.",
                    "backgroundSummary": [],
                    "suggestedNodeCount": 5,
                    "shouldSplit": False,
                }
            )
            mock_get_client.return_value = mock_client

            result = await AIService().parse_goal("Learn backpropagation", language="en-US")

    assert result.success is True
    assert result.data is not None
    assert result.data.title == "Understand the mathematical foundations of backpropagation in…"
