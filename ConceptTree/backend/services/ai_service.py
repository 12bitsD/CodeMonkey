"""AI Service - Real LLM Integration"""

from typing import Optional, AsyncGenerator

import asyncio
import json
import logging
from models import (
    ParseGoalResponse,
    ParseGoalAIResult,
    GenerateGraphResponse,
    GenerateGraphAIResult,
    GraphEdge,
    GraphNode,
    SkeletonGraph,
    SkeletonNode,
    GeneratedNodeContent,
    IntegrationResult,
    GraphNodeV2,
    GenerateGraphV2AIResult,
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

logger = logging.getLogger(__name__)


def _fallback_depth_level(learning_purpose: str) -> int:
    if learning_purpose == "explore":
        return 2
    if learning_purpose == "master":
        return 4
    return 3


def _build_fallback_graph(
    interpretation: str,
    learning_purpose: str = "apply",
) -> GenerateGraphResponse:
    goal = (interpretation or "当前学习目标").strip()
    depth_level = _fallback_depth_level(learning_purpose)
    target_count = {"explore": 5, "master": 10}.get(learning_purpose, 7)
    templates = [
        (
            "领域全景与目标拆解",
            "先建立整体地图，明确术语边界、学习目标和后续知识之间的关系。",
            ["领域核心问题", "关键术语边界", "学习目标拆解", "知识依赖关系"],
            ["能用自己的话说明学习目标", "能列出主要子主题"],
            "请围绕该学习目标建立一个整体知识地图。",
        ),
        (
            "基础概念与术语",
            "补齐后续学习会反复使用的基础概念，减少理解高级内容时的断点。",
            ["基础定义", "常见术语", "概念之间的区别", "典型使用场景"],
            ["能解释核心术语", "能区分容易混淆的概念"],
            "请解释这些基础概念，并给出容易混淆的对比。",
        ),
        (
            "核心机制与工作流程",
            "理解系统如何运转，是从会用走向会判断的关键。",
            ["输入输出关系", "核心流程", "关键约束", "常见失败模式", "调试思路"],
            ["能画出基本流程", "能说明每一步的作用"],
            "请拆解核心机制的完整工作流程。",
        ),
        (
            "方法与实践范式",
            "把概念转化为可执行步骤，形成稳定的实践方法。",
            ["基本操作步骤", "常用策略", "质量判断标准", "迭代改进方法"],
            ["能按步骤完成一个小任务", "能说明为什么这样做"],
            "请给出可操作的实践步骤和判断标准。",
        ),
        (
            "案例分析与迁移应用",
            "通过具体案例验证理解，并学习如何迁移到新的问题。",
            ["案例背景", "解决思路", "关键决策点", "迁移条件", "反例分析"],
            ["能分析一个案例", "能把方法迁移到相似场景"],
            "请用一个具体案例讲解如何应用这些知识。",
        ),
        (
            "工具链与资源选择",
            "掌握合适的工具和资料来源，提升学习与实践效率。",
            ["常用工具", "资料筛选标准", "练习资源", "记录与复盘方法"],
            ["能选择合适工具", "能规划后续练习资源"],
            "请推荐学习和实践该目标时适合使用的工具链。",
        ),
        (
            f"{goal[:24]}综合应用",
            "把前面的基础、机制和实践方法整合起来，完成面向目标的综合应用。",
            ["综合任务拆解", "方案设计", "执行检查点", "结果评估", "下一步优化"],
            ["能完成一个综合任务", "能评估结果并提出改进"],
            "请设计一个综合练习来检验我是否掌握该目标。",
        ),
        (
            "常见误区与边界条件",
            "识别误区和边界条件可以避免机械套用，提高判断质量。",
            ["高频误区", "边界条件", "适用与不适用场景", "纠错方法"],
            ["能指出常见误区", "能判断方法是否适用"],
            "请总结该主题的常见误区和边界条件。",
        ),
        (
            "进阶主题与扩展方向",
            "在掌握主线后识别更深层的扩展方向，形成长期学习路线。",
            ["进阶分支", "前沿问题", "深入阅读方向", "实践挑战"],
            ["能说明后续扩展路线", "能选择一个进阶方向继续学习"],
            "请给出该目标的进阶学习路线。",
        ),
        (
            "项目化验收",
            "通过项目化成果检验知识是否真正转化为能力。",
            ["项目目标", "验收标准", "风险清单", "复盘模板"],
            ["能定义项目验收标准", "能完成一次复盘"],
            "请设计一个项目化验收方案。",
        ),
    ][:target_count]

    nodes = []
    for index, (name, why, what, mastery, prompt) in enumerate(templates, start=1):
        is_target = index == len(templates)
        y = (index - len(templates)) * 160
        nodes.append(
            GraphNode(
                id=f"n{index}",
                name=name,
                status="unlearned",
                x=0 if is_target else ((index % 3) - 1) * 220,
                y=0 if is_target else y,
                why=why,
                what=what,
                mastery=mastery,
                prompt=prompt,
                resources=[],
                isTarget=is_target,
                domain="通用学习",
                depth_level=depth_level,
            )
        )

    edges = [
        GraphEdge(from_node=f"n{index}", to_node=f"n{index + 1}")
        for index in range(1, len(nodes))
    ]
    if len(nodes) >= 5:
        edges.extend(
            [
                GraphEdge(from_node="n2", to_node=nodes[-1].id),
                GraphEdge(from_node="n3", to_node=nodes[-1].id),
            ]
        )

    return GenerateGraphResponse(
        interpretation=goal,
        nodes=nodes,
        edges=edges,
        targetNodeId=nodes[-1].id,
    )


def _looks_like_incomplete_answer(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if stripped.endswith(("。", "！", "？", ".", "!", "?", "”", "）", ")", "]", "】")):
        return False
    if stripped.endswith(("\\", "=", "+", "-", ":", "：", ",", "，", ";", "；")):
        return True
    if stripped.count("\\[") > stripped.count("\\]"):
        return True
    if stripped.count("$$") % 2 == 1:
        return True
    return len(stripped) > 1200


def _repair_generated_graph(parsed: GenerateGraphResponse) -> GenerateGraphResponse:
    node_ids = {node.id for node in parsed.nodes}
    if not parsed.nodes:
        return parsed

    if parsed.targetNodeId not in node_ids:
        fallback_target = next((node for node in parsed.nodes if node.isTarget), None)
        parsed.targetNodeId = (fallback_target or parsed.nodes[-1]).id

    for node in parsed.nodes:
        node.isTarget = node.id == parsed.targetNodeId

    parsed.edges = [
        edge
        for edge in parsed.edges
        if edge.from_node in node_ids and edge.to_node in node_ids
    ]
    return parsed


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
                max_retries=1,
            )

            # Validate with Pydantic
            parsed = GenerateGraphResponse(**result)
            parsed = _repair_generated_graph(parsed)

            return GenerateGraphAIResult(success=True, data=parsed)

        except LLMServiceError as e:
            logger.warning(
                "generate_graph LLM failed, using fallback graph: %s", e
            )
            return GenerateGraphAIResult(
                success=True,
                data=_build_fallback_graph(interpretation, learning_purpose),
            )
        except ConfigLoadError as e:
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

    async def _run_phase1(
        self,
        interpretation: str,
        original_input: str,
        user_background: Optional[dict],
        learning_purpose: str,
    ) -> SkeletonGraph:
        """Phase 1: Curriculum Architect returns graph skeleton."""
        background_str = (
            json.dumps(user_background, ensure_ascii=False) if user_background else "无"
        )
        params, sys_prompt, usr_prompt = load_ai_config(
            "curriculum_architect",
            interpretation,
            original_input=original_input,
            background=background_str,
            learning_purpose=learning_purpose,
        )
        result = await self.llm_client.chat_json(
            system_prompt=sys_prompt,
            user_prompt=usr_prompt,
            temperature=params.get("temperature", 0.5),
            max_tokens=params.get("max_tokens", 2000),
            model=params.get("model"),
        )
        skeleton = SkeletonGraph(**result)
        node_ids = {node.id for node in skeleton.nodes}
        skeleton.edges = [
            edge
            for edge in skeleton.edges
            if edge.from_node in node_ids and edge.to_node in node_ids
        ]
        if skeleton.targetNodeId not in node_ids and skeleton.nodes:
            skeleton.targetNodeId = skeleton.nodes[-1].id
        return skeleton

    async def _run_phase2_node(
        self,
        node: SkeletonNode,
        all_nodes: list[SkeletonNode],
        edges: list,
        learning_goal: str,
        learning_purpose: str,
        semaphore: asyncio.Semaphore,
    ) -> GeneratedNodeContent:
        """Phase 2: Content Generator creates content for one node."""
        neighbor_names = ", ".join(n.name for n in all_nodes if n.id != node.id)
        prerequisite_ids = {e.from_node for e in edges if e.to_node == node.id}
        prerequisite_names = (
            ", ".join(n.name for n in all_nodes if n.id in prerequisite_ids) or "无"
        )

        params, sys_prompt, usr_prompt = load_ai_config(
            "content_generator",
            f"{node.id}: {node.name}（领域：{node.domain or '通用'}）",
            learning_goal=learning_goal,
            learning_purpose=learning_purpose,
            neighbor_names=neighbor_names,
            prerequisite_names=prerequisite_names,
        )

        async with semaphore:
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.7),
                max_tokens=params.get("max_tokens", 1500),
                model=params.get("model"),
            )

        result["node_id"] = node.id
        return GeneratedNodeContent(**result)

    async def _run_phase3(
        self,
        contents: list[GeneratedNodeContent],
        learning_goal: str,
    ) -> IntegrationResult:
        """Phase 3: Integration Agent deduplicates what lists across nodes."""
        nodes_payload = json.dumps(
            [
                {"node_id": c.node_id, "name_hint": c.node_id, "what": c.what}
                for c in contents
            ],
            ensure_ascii=False,
        )
        params, sys_prompt, usr_prompt = load_ai_config(
            "integration_agent",
            nodes_payload,
            learning_goal=learning_goal,
        )
        try:
            result = await self.llm_client.chat_json(
                system_prompt=sys_prompt,
                user_prompt=usr_prompt,
                temperature=params.get("temperature", 0.2),
                max_tokens=params.get("max_tokens", 3000),
                model=params.get("model"),
            )
            return IntegrationResult(**result)
        except Exception:
            return IntegrationResult(revised_nodes=[])

    async def generate_graph_v2_stream(
        self,
        interpretation: str,
        original_input: str,
        user_background: Optional[dict],
        learning_purpose: str,
    ) -> AsyncGenerator[str, None]:
        """
        Multi-agent graph generation, yielding SSE-formatted strings.
        """

        def _sse(payload: dict) -> str:
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        try:
            skeleton = await self._run_phase1(
                interpretation, original_input, user_background, learning_purpose
            )
        except Exception as e:
            yield _sse(
                {
                    "type": "error",
                    "data": {"code": "PHASE1_FAILED", "message": str(e)},
                }
            )
            return

        yield _sse(
            {
                "type": "skeleton",
                "data": {
                    "nodes": [n.model_dump() for n in skeleton.nodes],
                    "edges": [e.model_dump() for e in skeleton.edges],
                    "targetNodeId": skeleton.targetNodeId,
                    "total_nodes": len(skeleton.nodes),
                },
            }
        )
        await asyncio.sleep(0)

        semaphore = asyncio.Semaphore(8)
        node_futures = [
            asyncio.ensure_future(
                self._run_phase2_node(
                    node=node,
                    all_nodes=skeleton.nodes,
                    edges=skeleton.edges,
                    learning_goal=interpretation,
                    learning_purpose=learning_purpose,
                    semaphore=semaphore,
                )
            )
            for node in skeleton.nodes
        ]

        completed_contents: list[GeneratedNodeContent] = []
        pending = set(node_futures)
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for fut in done:
                try:
                    content = fut.result()
                    completed_contents.append(content)
                    yield _sse({"type": "node_ready", "data": content.model_dump()})
                    await asyncio.sleep(0)
                except Exception as e:
                    yield _sse(
                        {"type": "node_error", "data": {"message": str(e)}}
                    )

        integration = await self._run_phase3(completed_contents, interpretation)
        yield _sse({"type": "integration_done", "data": integration.model_dump()})
        await asyncio.sleep(0)

        yield _sse({"type": "done"})

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
        emitted = []
        async for chunk in self.llm_client.chat_stream(
            messages=session["messages"],
            temperature=session["temperature"],
            max_tokens=session["max_tokens"],
            model=session["model"],
        ):
            emitted.append(chunk)
            yield chunk

        partial = "".join(emitted)
        if not _looks_like_incomplete_answer(partial):
            return

        continuation_messages = [
            *session["messages"],
            LLMMessage(role="assistant", content=partial),
            LLMMessage(
                role="user",
                content=(
                    "你的上一条回答明显还没有结束。请从中断处继续，"
                    "不要重复已经说过的内容，直接补完剩余推导或结论。"
                ),
            ),
        ]
        yield "\n\n"
        async for chunk in self.llm_client.chat_stream(
            messages=continuation_messages,
            temperature=session["temperature"],
            max_tokens=min(session["max_tokens"], 2048),
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
