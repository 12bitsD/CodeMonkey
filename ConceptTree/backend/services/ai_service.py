"""AI Service - Real LLM Integration"""

import json
from typing import Optional
from jinja2 import Template, StrictUndefined

from models import (
    ParseGoalResponse,
    ParseGoalAIResult,
    GenerateGraphResponse,
    GenerateGraphAIResult,
    ApiError,
)
from services.llm import get_llm_client, LLMServiceError
from services.llm.prompts import load_prompt, PARSE_GOAL_V1, GENERATE_GRAPH_V1


class AIService:
    """AI service for learning goal parsing and graph generation"""

    def __init__(self):
        self.llm_client = get_llm_client()

    async def parse_goal(self, user_input: str) -> ParseGoalAIResult:
        """
        Parse user learning goal using LLM.

        Args:
            user_input: Raw user input describing what they want to learn

        Returns:
            ParseGoalAIResult with structured data or error
        """
        try:
            # Load and render prompt
            prompt_template = load_prompt(PARSE_GOAL_V1)
            prompt = Template(prompt_template, undefined=StrictUndefined).render(
                user_input=user_input
            )

            # Call LLM
            result = await self.llm_client.chat_json(
                system_prompt="You are a helpful learning assistant.",
                user_prompt=prompt,
                temperature=0.7,
            )

            # Validate with Pydantic
            parsed = ParseGoalResponse(**result)

            return ParseGoalAIResult(success=True, data=parsed)

        except LLMServiceError as e:
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

            # Load and render prompt
            prompt_template = load_prompt(GENERATE_GRAPH_V1)
            prompt = Template(prompt_template, undefined=StrictUndefined).render(
                interpretation=interpretation,
                original_input=original_input,
                background=background_str,
            )

            # Call LLM
            result = await self.llm_client.chat_json(
                system_prompt="You are a helpful learning assistant.",
                user_prompt=prompt,
                temperature=0.7,
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

        except LLMServiceError as e:
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


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI service singleton"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
