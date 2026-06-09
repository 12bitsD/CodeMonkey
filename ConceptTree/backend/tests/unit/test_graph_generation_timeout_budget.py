from config import settings
from routers import ai as ai_router


def test_graph_generation_timeout_exceeds_llm_retry_budget():
    llm_retry_budget = settings.LLM_TIMEOUT * settings.LLM_MAX_RETRIES
    assert ai_router.GRAPH_GENERATION_TIMEOUT_SECONDS >= llm_retry_budget + 30
