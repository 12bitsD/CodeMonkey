import asyncio

from services.ai_service import AIService
from services.llm import LLMServiceError


def test_generate_graph_returns_fallback_graph_when_llm_times_out():
    class SlowLLM:
        async def chat_json(self, *args, **kwargs):
            raise LLMServiceError("Request timed out after 45s")

    service = AIService.__new__(AIService)
    service.llm_client = SlowLLM()

    result = asyncio.run(
        service.generate_graph(
            interpretation="systematic LLM basics and prompt engineering",
            original_input="learn LLM basics and prompt engineering",
            learning_purpose="apply",
        )
    )

    assert result.success is True
    assert result.data.interpretation == "systematic LLM basics and prompt engineering"
    assert len(result.data.nodes) >= 5
    assert result.data.targetNodeId in {node.id for node in result.data.nodes}
    assert all(node.what for node in result.data.nodes)


def test_generate_graph_uses_single_llm_attempt_before_fallback():
    class RecordingLLM:
        def __init__(self):
            self.kwargs = None

        async def chat_json(self, *args, **kwargs):
            self.kwargs = kwargs
            return {
                "interpretation": "goal",
                "nodes": [
                    {
                        "id": "n1",
                        "name": "Target Node",
                        "why": "why",
                        "what": ["what"],
                        "mastery": ["mastery"],
                        "prompt": "prompt",
                        "isTarget": True,
                    }
                ],
                "edges": [],
                "targetNodeId": "n1",
            }

    llm = RecordingLLM()
    service = AIService.__new__(AIService)
    service.llm_client = llm

    result = asyncio.run(
        service.generate_graph(
            interpretation="goal",
            original_input="goal",
            learning_purpose="apply",
        )
    )

    assert result.success is True
    assert llm.kwargs["max_retries"] == 1
