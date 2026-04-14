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


class AIService:
    """AI service for learning goal parsing and graph generation"""

    def __init__(self):
        self.llm_client = get_llm_client()

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
    ) -> AsyncGenerator[str, None]:
        """
        F4: Stream a chat response given message history + node context.

        Yields text chunks from the LLM.
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
        for msg in messages_input:
            llm_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        async for chunk in self.llm_client.chat_stream(
            messages=llm_messages,
            temperature=params.get("temperature", 0.7),
            max_tokens=params.get("max_tokens", 1024),
            model=params.get("model"),
        ):
            yield chunk


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
