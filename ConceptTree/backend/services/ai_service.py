"""AI Service - Real LLM Integration"""

from typing import Optional, AsyncGenerator

import json
from models import (
    ParseGoalResponse,
    ParseGoalAIResult,
    GenerateGraphResponse,
    GenerateGraphAIResult,
    ClarifyGoalResponse,
    ClarifyGoalAIResult,
    RecommendNextResponse,
    RecommendNextAIResult,
    ApiError,
)
from services.llm import get_llm_client, LLMServiceError
from services.llm.configs import load_ai_config, ConfigLoadError
from services.llm.providers import LLMMessage
from services.search_service import SearchServiceError, get_search_service


class AIService:
    """AI service for learning goal parsing and graph generation"""

    def __init__(self):
        self.llm_client = get_llm_client()
        self.search_service = get_search_service()

    async def parse_goal(
        self, user_input: str, user_background: Optional[dict] = None
    ) -> ParseGoalAIResult:
        """
        Parse user learning goal using LLM.

        Args:
            user_input: Raw user input describing what they want to learn

        Returns:
            ParseGoalAIResult with structured data or error
        """
        try:
            background_str = (
                json.dumps(user_background, ensure_ascii=False)
                if user_background
                else "无"
            )

            # Load config and build prompt
            params, sys_prompt, usr_prompt = load_ai_config(
                "parse_goal", user_input, background=background_str
            )

            # Call LLM with config-driven parameters
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 4096),
            )

            # Validate with Pydantic
            parsed = ParseGoalResponse(**result)

            return ParseGoalAIResult(success=True, data=parsed)

        except (LLMServiceError, ConfigLoadError) as e:
            return ParseGoalAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}"
                ),
            )
        except Exception as e:
            return ParseGoalAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"Failed to parse goal: {str(e)}"
                ),
            )

    async def generate_graph(
        self,
        interpretation: str,
        original_input: str,
        user_background: Optional[dict] = None,
        learning_purpose: str = "apply",
    ) -> GenerateGraphAIResult:
        """
        Generate knowledge graph using LLM.

        Args:
            interpretation: Parsed learning goal
            original_input: Original user input
            user_background: Optional user profile data

        Returns:
            GenerateGraphAIResult with graph data or error
        """
        try:
            # Format background for prompt
            background_str = (
                json.dumps(user_background, ensure_ascii=False)
                if user_background
                else "无"
            )

            # Load config and build prompt (learning_purpose substituted into system_prompt)
            params, sys_prompt, usr_prompt = load_ai_config(
                "generate_graph",
                interpretation,
                original_input=original_input,
                background=background_str,
                learning_purpose=learning_purpose,
            )

            # Call LLM with config-driven parameters (model override for speed)
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 4096),
                model=params.get("model"),
            )

            # Validate with Pydantic
            parsed = GenerateGraphResponse(**result)

            # Validate target node exists
            target_exists = any(node.id == parsed.targetNodeId for node in parsed.nodes)
            if not target_exists:
                return GenerateGraphAIResult(
                    success=False,
                    error=ApiError(
                        code="AI_SERVICE_ERROR",
                        message="Generated graph has invalid target node",
                    ),
                )

            # Validate edge references
            node_ids = {node.id for node in parsed.nodes}
            for edge in parsed.edges:
                if edge.from_node not in node_ids or edge.to_node not in node_ids:
                    return GenerateGraphAIResult(
                        success=False,
                        error=ApiError(
                            code="AI_SERVICE_ERROR",
                            message="Generated graph has invalid edge references",
                        ),
                    )

            return GenerateGraphAIResult(success=True, data=parsed)

        except (LLMServiceError, ConfigLoadError) as e:
            return GenerateGraphAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}"
                ),
            )
        except Exception as e:
            return GenerateGraphAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR",
                    message=f"Failed to generate graph: {str(e)}",
                ),
            )

    async def clarify_goal(
        self,
        original_goal: str,
        new_goal: str,
        existing_nodes: Optional[list] = None,
    ) -> ClarifyGoalAIResult:
        try:
            nodes_context = ""
            if existing_nodes:
                nodes_list = "\n".join(
                    f"  - id={n['id']}, name={n['name']}, status={n['status']}"
                    for n in existing_nodes
                )
                nodes_context = f"\nExisting nodes:\n{nodes_list}"

            combined_input = (
                f"original: {original_goal}, new: {new_goal}{nodes_context}"
            )
            params, sys_prompt, usr_prompt = load_ai_config(
                "clarify_goal", combined_input
            )

            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.3),
                max_tokens=params.get("max_tokens", 2000),
            )

            parsed = ClarifyGoalResponse(**result)
            return ClarifyGoalAIResult(success=True, data=parsed)

        except (LLMServiceError, ConfigLoadError) as e:
            return ClarifyGoalAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}"
                ),
            )
        except Exception as e:
            return ClarifyGoalAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"Failed to clarify goal: {str(e)}"
                ),
            )

    async def recommend_next(
        self,
        graph: dict,
        user_profile: dict,
        learning_history: dict,
        learning_goal: str,
    ) -> RecommendNextAIResult:
        try:
            context = json.dumps(
                {
                    "graph": graph,
                    "user_profile": user_profile,
                    "learning_history": learning_history,
                    "learning_goal": learning_goal,
                },
                ensure_ascii=False,
            )
            params, sys_prompt, usr_prompt = load_ai_config("recommend_next", context)

            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.5),
                max_tokens=params.get("max_tokens", 1024),
            )

            parsed = RecommendNextResponse(**result)
            return RecommendNextAIResult(success=True, data=parsed)

        except (LLMServiceError, ConfigLoadError) as e:
            return RecommendNextAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"AI service error: {str(e)}"
                ),
            )
        except Exception as e:
            return RecommendNextAIResult(
                success=False,
                error=ApiError(
                    code="AI_SERVICE_ERROR", message=f"Failed to recommend: {str(e)}"
                ),
            )


    async def explain_topic_stream(
        self,
        topic_text: str,
        node_name: str,
        plan_title: Optional[str] = None,
        why: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        F7: Stream an explanation for a specific what-item topic.

        Yields text chunks from the LLM.
        """
        import json as _json
        from pathlib import Path

        config_path = Path(__file__).parent / "llm/configs/explain_topic.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = _json.load(f)
        except Exception:
            config = {"model_params": {}, "system_prompt": "你是专业学习教练，请详细解释给定主题。"}

        params = config.get("model_params", {})
        system_prompt = config.get("system_prompt", "")

        context_parts = [f"正在学习的节点：{node_name}"]
        if plan_title:
            context_parts.append(f"学习计划：{plan_title}")
        if why:
            context_parts.append(f"学习原因：{why}")
        context_str = "\n".join(context_parts)

        user_prompt = f"{context_str}\n\n请解释以下主题：{topic_text}"

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        async for chunk in self.llm_client.chat_stream(
            messages=messages,
            temperature=params.get("temperature", 0.5),
            max_tokens=params.get("max_tokens", 1024),
            model=params.get("model"),
        ):
            yield chunk

    async def chat_stream(
        self,
        messages_input: list,
        node_name: str = "",
        plan_title: Optional[str] = None,
        enable_web_search: bool = False,
    ) -> AsyncGenerator[str, None]:
        """F4: Stream a chat response given message history + node context."""
        session = await self.prepare_chat_session(
            messages_input=messages_input,
            node_name=node_name,
            plan_title=plan_title,
            enable_web_search=enable_web_search,
        )

        async for chunk in self.stream_chat_session(session):
            yield chunk

    async def prepare_chat_session(
        self,
        messages_input: list,
        node_name: str = "",
        plan_title: Optional[str] = None,
        enable_web_search: bool = False,
    ) -> dict:
        """
        Build the LLM chat payload and optionally enrich it with web-search context.

        Returns a dict containing llm messages, model params, search status and sources.
        """
        import json as _json
        from pathlib import Path

        config_path = Path(__file__).parent / "llm/configs/chat.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = _json.load(f)
        except Exception:
            config = {"model_params": {}, "system_prompt": "你是学习辅导助手，请用中文回答问题。"}

        params = config.get("model_params", {})
        system_prompt = config.get("system_prompt", "")
        system_prompt = system_prompt.replace("{{node_name}}", node_name)
        system_prompt = system_prompt.replace("{{plan_title}}", plan_title or "")

        llm_messages = [LLMMessage(role="system", content=system_prompt)]
        sources: list[dict] = []
        search_status = "disabled"

        if enable_web_search:
            latest_user_message = next(
                (
                    str(msg.get("content", "")).strip()
                    for msg in reversed(messages_input)
                    if msg.get("role") == "user" and str(msg.get("content", "")).strip()
                ),
                "",
            )
            if latest_user_message:
                try:
                    sources = await self.search_service.search(latest_user_message)
                    search_status = "done" if sources else "fallback"
                except SearchServiceError:
                    sources = []
                    search_status = "fallback"
            else:
                search_status = "fallback"

        if sources:
            llm_messages.append(
                LLMMessage(
                    role="system",
                    content=self._build_search_context(sources),
                )
            )

        for msg in messages_input:
            llm_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        return {
            "messages": llm_messages,
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 1024),
            "model": params.get("model"),
            "sources": sources,
            "search_status": search_status,
        }

    async def stream_chat_session(self, session: dict) -> AsyncGenerator[str, None]:
        async for chunk in self.llm_client.chat_stream(
            messages=session["messages"],
            temperature=session["temperature"],
            max_tokens=session["max_tokens"],
            model=session["model"],
        ):
            yield chunk

    def _build_search_context(self, sources: list[dict]) -> str:
        source_lines = []
        for index, source in enumerate(sources, start=1):
            source_lines.append(
                "\n".join(
                    [
                        f"[来源 {index}]",
                        f"标题：{source.get('title', '')}",
                        f"链接：{source.get('url', '')}",
                        f"摘要：{source.get('snippet', '')}",
                    ]
                )
            )

        sources_block = "\n\n".join(source_lines)
        return (
            "以下是联网搜索结果，请优先依据这些资料回答。"
            "如果搜索结果不足以支持结论，请明确说明不确定性，不要编造来源。\n\n"
            f"{sources_block}"
        )


    async def summarize_resource_results(
        self,
        node_name: str,
        query: str,
        results: list[dict],
    ) -> dict[str, str]:
        """Generate short AI summaries for searched resources keyed by URL."""
        if not results:
            return {}

        prompt_payload = json.dumps(
            {
                "node_name": node_name,
                "query": query,
                "results": [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                    }
                    for item in results
                ],
            },
            ensure_ascii=False,
        )

        system_prompt = (
            "你是学习资源整理助手。"
            "请根据每条资源的标题与摘要，输出简短、准确、适合卡片展示的中文简介。"
            "每条简介控制在18到36个中文字符之间，不要使用编号，不要重复标题。"
            '只返回 JSON，格式为 {"items":[{"url":"...","summary":"..."}]}。'
        )
        user_prompt = (
            f"请为知识点“{node_name}”的联网搜索结果生成资源简介。\n\n"
            f"{prompt_payload}"
        )

        try:
            result = await self.llm_client.chat_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=1200,
            )
        except Exception:
            return {}

        items = result.get("items", [])
        summary_map: dict[str, str] = {}
        for item in items:
            url = str(item.get("url", "")).strip()
            summary = str(item.get("summary", "")).strip()
            if url and summary:
                summary_map[url] = summary
        return summary_map


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
