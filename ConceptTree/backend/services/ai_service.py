"""Orchestrates the four AI-powered learning workflows for ConceptTree.

This module is the primary entry point for all LLM calls in the backend.
Each of the four public methods maps 1-to-1 with a user-facing operation:
parse a goal, generate a knowledge graph, clarify an updated goal, and
recommend the next concept to study.

Primary reader: backend developer adding a new AI endpoint or tracing a
request through the AI pipeline.

Key things to understand:
  1. **Config-driven prompts** — no prompt text is hard-coded here; each
     method loads its system/user prompt from a JSON file in
     ``services/llm/configs/`` via :func:`~services.llm.configs.load_ai_config`.
  2. **Error containment** — every exception is caught and converted to an
     ``ApiError`` embedded in the typed ``AIResult`` object; callers never
     receive a raw exception.
  3. **Singleton client** — all methods share one :class:`~services.llm.client.UnifiedLLMClient`
     instance (and its HTTP connection pool) via :func:`get_ai_service`.
"""

from typing import Optional

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


class AIService:
    """Executes the four LLM-powered learning workflows for ConceptTree.

    This class sits between the HTTP route layer and the LLM client layer.
    It is responsible for:

    - Loading the correct prompt configuration from ``services/llm/configs/``
      by name (e.g. ``"parse_goal"`` → ``parse_goal.json``).
    - Invoking :class:`~services.llm.client.UnifiedLLMClient` with the
      assembled prompts and config-driven temperature / max-token settings.
    - Validating the structured JSON response with the matching Pydantic model.
    - Catching every exception and converting it to a typed ``AIResult``
      (``success=False``, ``error=ApiError``), so HTTP route handlers always
      receive a consistent response shape regardless of what went wrong.

    Instantiate once via :func:`get_ai_service` (singleton).  Each method
    call is stateless — no shared mutable state is modified at call time.
    """

    def __init__(self):
        """Wire the shared LLM client on first instantiation."""
        self.llm_client = get_llm_client()

    async def parse_goal(self, user_input: str) -> ParseGoalAIResult:
        """Turn free-form user text into a structured learning profile.

        Uses the ``parse_goal`` prompt config to extract:

        - A clear, actionable learning objective (``interpretation``).
        - Background strengths and weaknesses inferred from the user's text.
        - An estimated node count and, if the goal is too broad, split
          suggestions for breaking it into focused sub-goals.

        Args:
            user_input: Raw text describing what the user wants to learn,
                e.g. ``"I want to learn Python data analysis"``.

        Returns:
            :class:`~models.ParseGoalAIResult` with ``success=True`` and
            ``data`` populated on success, or ``success=False`` with an
            ``ApiError`` (code ``"AI_SERVICE_ERROR"``) on any LLM or config
            failure.
        """
        try:
            # Load config and build prompt
            params, sys_prompt, usr_prompt = load_ai_config("parse_goal", user_input)

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
    ) -> GenerateGraphAIResult:
        """Build a knowledge dependency graph tailored to the learning goal.

        Uses the ``generate_graph`` prompt config to produce a directed graph
        of prerequisite concepts (nodes) and their dependencies (edges), with
        one designated target node representing the final learning objective.

        After receiving the LLM response, this method validates structural
        integrity before returning:

        - The ``targetNodeId`` must reference an existing node.
        - Every edge's ``from_node`` and ``to_node`` must reference existing
          node IDs.

        Args:
            interpretation: The structured learning objective produced by
                :meth:`parse_goal` — used as the primary prompt input.
            original_input: The user's original free-form text, included in
                the prompt for additional context.
            user_background: Optional dict of user profile data (strengths,
                weaknesses) serialised into the prompt so the LLM can adapt
                the graph — for example, skipping nodes the user already knows.
                Pass ``None`` if no profile is available; the prompt will
                receive ``"无"`` (none) for this field.

        Returns:
            :class:`~models.GenerateGraphAIResult` with ``success=True`` and
            a validated :class:`~models.GenerateGraphResponse` on success, or
            ``success=False`` with an ``ApiError`` describing the failure
            (LLM error, invalid target node, or broken edge reference).
        """
        try:
            # Format background for prompt
            background_str = (
                json.dumps(user_background, ensure_ascii=False)
                if user_background
                else "无"
            )

            # Load config and build prompt
            params, sys_prompt, usr_prompt = load_ai_config(
                "generate_graph",
                interpretation,
                original_input=original_input,
                background=background_str,
            )

            # Call LLM with config-driven parameters
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 4096),
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
        """Detect how much a revised goal diverges from the current learning plan.

        Uses the ``clarify_goal`` prompt config to classify the change as a
        refinement (``suggestion="modify"``) or a fundamentally new subject
        (``suggestion="create_new"``), and to produce a diff of node IDs:

        - ``changes.keep`` — existing node IDs to preserve in the plan.
        - ``changes.remove`` — existing node IDs to delete from the plan.
        - ``changes.add`` — new concept names (strings) not yet in the plan.

        The LLM references ``existing_nodes`` by their exact ``id`` values,
        so this method formats them as ``id=n1, name=..., status=...`` lines
        before passing them to the config assembler.

        Args:
            original_goal: The learning objective the user started with.
            new_goal: The user's revised learning objective.
            existing_nodes: Optional list of current plan nodes, each a dict
                with keys ``id``, ``name``, and ``status``.  The LLM uses
                these exact ``id`` values in ``changes.keep``/``changes.remove``.
                Pass ``None`` or an empty list if no plan exists yet.

        Returns:
            :class:`~models.ClarifyGoalAIResult` with ``success=True`` and a
            :class:`~models.ClarifyGoalResponse` on success, or
            ``success=False`` with an ``ApiError`` on any failure.
        """
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
        """Recommend the single best next concept for the user to study.

        Serialises the full graph, user profile, learning history, and goal
        into a JSON context string and passes it to the ``recommend_next``
        prompt config.  The LLM returns the ``id`` of the recommended node
        and a one-sentence Chinese reason.

        The LLM enforces prerequisite ordering: it only recommends nodes
        whose incoming prerequisite edges all point to ``learned`` or
        ``skipped`` nodes, and it prefers nodes on the critical path to the
        target.  If every node is already completed, ``recommended_node_id``
        will be ``null``.

        Args:
            graph: The full knowledge graph dict (nodes + edges) for the
                current learning plan.
            user_profile: User profile dict (e.g. ``math_level``,
                ``experience``) used to personalise the recommendation —
                weaker profiles receive more foundational suggestions.
            learning_history: Dict produced by
                :func:`~services.learning_history.get_learning_history`,
                containing at minimum ``learned_nodes`` and ``skipped_nodes``
                lists of node IDs.
            learning_goal: The user's learning objective string, provided
                to the LLM as additional context.

        Returns:
            :class:`~models.RecommendNextAIResult` with ``success=True`` and
            a :class:`~models.RecommendNextResponse` (containing
            ``recommended_node_id`` and ``reason``) on success, or
            ``success=False`` with an ``ApiError`` on any failure.
        """
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


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Return the shared :class:`AIService` instance, creating it on first call.

    Uses the singleton pattern so the underlying LLM client (and its HTTP
    connection pool) is initialised once and reused across all requests,
    rather than re-created on every call.

    Returns:
        The application-wide :class:`AIService` singleton.
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
