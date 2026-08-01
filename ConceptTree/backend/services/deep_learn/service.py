from __future__ import annotations

import json
import logging
import asyncio
import re
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from uuid import uuid4

from fastapi import BackgroundTasks

from database import DbSession, get_db_context
from models_deep_learn import (
    AssessmentOverallOutput,
    DeepLearnCommand,
    SessionState,
    TeachingMode,
)
from models_memory import MemoryEvent
from services.deep_learn.agents.assessment_overall import AssessmentOverallAgent
from services.deep_learn.agents.assessment_per_question import AssessmentPerQuestionAgent
from services.deep_learn.agents.image_trigger import ImageTriggerAgent
from services.deep_learn.agents.note_generator import NoteGeneratorAgent
from services.deep_learn.agents.teaching import TeachingAgent
from services.deep_learn import image_storage
from services.deep_learn.notes_repo import save_completion_note
from services.deep_learn.memory.context_builder import MemoryContextBuilder
from services.deep_learn.memory.update_service import MemoryUpdateService
from services.deep_learn.session_repo import (
    abandon_session,
    create_session,
    get_active_session,
    get_session_by_id,
    update_session,
)
from services.deep_learn.state_machine import (
    decide_on_assessment_done,
    decide_on_command,
    decide_on_final_judge,
    decide_on_init,
    decide_on_readiness_done,
    decide_on_user_message,
)
from services.llm.client import get_llm_client
from services.llm.language import apply_response_language

logger = logging.getLogger(__name__)

# Patterns that suggest a definition worth noting
_DEFINITION_PATTERNS = re.compile(
    r"(是指|是一种|指的是|定义为|称为|即|就是说|也就是).{5,80}[。！；\n]",
    re.UNICODE,
)
_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


def _sse(event_type: str, **data) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


def _split_text_for_streaming(text: str, chunk_size: int = 48) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    soft_breaks = set("。！？；\n")

    for char in text:
        current.append(char)
        current_len += 1
        if current_len >= chunk_size or (current_len >= 12 and char in soft_breaks):
            chunks.append("".join(current))
            current = []
            current_len = 0

    if current:
        chunks.append("".join(current))

    return chunks


def _maybe_emit_note_suggestion(content: str) -> Optional[str]:
    """Extract a note-worthy snippet if content has a clear definition sentence."""
    m = _DEFINITION_PATTERNS.search(content)
    if not m:
        return None
    # Find the sentence boundary before the match
    start = content.rfind("。", 0, m.start())
    start = start + 1 if start >= 0 else 0
    snippet = content[start:m.end()].strip()
    if len(snippet) > 120:
        snippet = snippet[:120] + "…"
    return snippet if len(snippet) >= 10 else None


async def _generate_test_questions(
    node_name: str,
    what_list: list[str],
    weak_points: list[str],
    language: str = "zh-CN",
) -> list[str]:
    system = "你是出题专家。根据节点内容生成 3 道综合测试题，测试用户对整个节点的掌握程度。仅返回 JSON：{\"questions\": [\"题1\",\"题2\",\"题3\"]}"
    system = apply_response_language(system, language, json_mode=True)
    weak_str = "、".join(weak_points) if weak_points else "无"
    user = (
        f"节点：{node_name}\n"
        f"概念列表：{what_list}\n"
        f"已知弱点：{weak_str}\n"
        "请出 3 道综合测试题，覆盖核心概念，兼顾弱点。"
    )
    try:
        raw = await get_llm_client().chat_json(system, user, temperature=0.4, max_tokens=800)
        qs = raw.get("questions", [])
        if len(qs) >= 3:
            return qs[:3]
    except Exception as e:
        logger.error("_generate_test_questions failed: %s", e)
    if language == "zh-CN":
        return [
            f"请用自己的话解释 {what_list[0] if what_list else node_name} 的核心原理。",
            f"举一个 {node_name} 在实际场景中的应用例子。",
            f"列举学习 {node_name} 时常见的误区或陷阱。",
        ]
    return [
        f"Explain the core principle of {what_list[0] if what_list else node_name} in your own words.",
        f"Give one practical example of {node_name}.",
        f"Identify common misconceptions or pitfalls when learning {node_name}.",
    ]


class DeepLearnService:
    def __init__(self) -> None:
        self.teaching_agent = TeachingAgent()
        self.assessment_per_q = AssessmentPerQuestionAgent()
        self.assessment_overall = AssessmentOverallAgent()
        self.memory_builder = MemoryContextBuilder()
        self.memory_updater = MemoryUpdateService()
        self.image_trigger = ImageTriggerAgent()
        self.note_generator = NoteGeneratorAgent()
        self._localized_node_cache: dict[str, dict] = {}

    async def localize_node_meta(self, node_meta: dict, language: str) -> dict:
        """Return display/agent metadata in the requested UI language.

        Learning maps keep their original authored language in storage. This
        translation layer lets an existing Chinese map render and teach in
        English (and vice versa) without mutating the saved graph.
        """
        target_language = "zh-CN" if language == "zh-CN" else "en-US"
        source = {
            "node_name": str(node_meta.get("node_name") or ""),
            "node_why": str(node_meta.get("node_why") or ""),
            "what_list": [str(item) for item in (node_meta.get("what_list") or [])],
        }
        combined = " ".join([source["node_name"], source["node_why"], *source["what_list"]])
        has_cjk = bool(_CJK_PATTERN.search(combined))
        if (target_language == "en-US" and not has_cjk) or (target_language == "zh-CN" and has_cjk):
            return source

        cache_key = json.dumps(
            {"language": target_language, "source": source},
            ensure_ascii=False,
            sort_keys=True,
        )
        cached = self._localized_node_cache.get(cache_key)
        if cached:
            return dict(cached)

        target_name = "natural English" if target_language == "en-US" else "Simplified Chinese"
        system_prompt = (
            f"Translate learning-map metadata into {target_name}. "
            "Preserve technical meaning, formulas, symbols, library names, and list order. "
            "Do not add explanations. Return only a JSON object with exactly these keys: "
            "node_name (string), node_why (string), what_list (array of strings)."
        )
        user_prompt = json.dumps(source, ensure_ascii=False)
        try:
            translated = await get_llm_client().chat_json(
                system_prompt,
                user_prompt,
                temperature=0.0,
                max_tokens=1200,
                max_retries=2,
            )
            translated_list = translated.get("what_list")
            if (
                not isinstance(translated.get("node_name"), str)
                or not isinstance(translated.get("node_why"), str)
                or not isinstance(translated_list, list)
                or len(translated_list) != len(source["what_list"])
                or not all(isinstance(item, str) and item.strip() for item in translated_list)
            ):
                raise ValueError("localized node metadata has an invalid shape")
            result = {
                "node_name": translated["node_name"].strip(),
                "node_why": translated["node_why"].strip(),
                "what_list": [item.strip() for item in translated_list],
            }
            self._localized_node_cache[cache_key] = result
            return dict(result)
        except Exception as error:
            logger.warning("node metadata localization failed; using source text: %s", error)
            return source

    async def get_or_create_session(
        self, *, db: DbSession, user_id: str, node_id: str, plan_id: str,
    ) -> tuple[SessionState, dict]:
        existing = get_active_session(db, user_id, node_id)
        if existing:
            node_meta = self._fetch_node_meta(db, node_id)
            return existing, node_meta

        node_meta = self._fetch_node_meta(db, node_id)
        what_list = node_meta.get("what_list", [])
        session = create_session(db, user_id=user_id, node_id=node_id, plan_id=plan_id, what_list=what_list)
        return session, node_meta

    def _fetch_node_meta(self, db: DbSession, node_id: str) -> dict:
        row = db.execute(
            "SELECT name, why, what FROM nodes WHERE id=?", (node_id,)
        ).fetchone()
        if not row:
            return {"node_name": "", "node_why": "", "what_list": []}
        what = row["what"] or []
        if isinstance(what, str):
            try:
                what = json.loads(what)
            except Exception:
                what = []
        return {
            "node_name": row["name"] or "",
            "node_why": row["why"] or "",
            "what_list": what,
        }

    async def stream_initialize(
        self, session: SessionState, node_meta: dict,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        try:
            if session.state != "INITIALIZING":
                yield _sse("error", error={"code": "INVALID_STATE", "message": f"session state is {session.state}, not INITIALIZING"})
                return

            teach_kwargs = {
                "mode": "normal",
                "background_tasks": background_tasks,
            }
            if language != "zh-CN":
                teach_kwargs["language"] = language
            async for event in self._run_teach(session, node_meta, **teach_kwargs):
                yield event
        except Exception as e:
            logger.exception("stream_initialize error")
            yield _sse("error", error={"code": "INTERNAL_ERROR", "message": str(e)})
        finally:
            yield _sse("done")

    async def stream_message(
        self, session: SessionState, node_meta: dict, content: str,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        try:
            decision = decide_on_user_message(
                session.state,
                session.wrong_count_current,
                session.state == "TESTING",
            )

            with get_db_context() as db:
                new_turns = (session.recent_turns + [{"role": "user", "content": content}])[-8:]
                update_session(db, session.id, recent_turns=new_turns)
            session.recent_turns = new_turns

            if decision.action == "assess_per_question":
                is_test = session.state == "TESTING"
                async for event in self._run_assessment(session, node_meta, content, is_test, background_tasks=background_tasks, language=language):
                    yield event
            else:
                yield _sse("error", error={"code": "INVALID_STATE", "message": f"cannot handle message in state {session.state}"})

        except Exception as e:
            logger.exception("stream_message error")
            yield _sse("error", error={"code": "INTERNAL_ERROR", "message": str(e)})
        finally:
            yield _sse("done")

    async def stream_command(
        self, session: SessionState, node_meta: dict, command: DeepLearnCommand,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        try:
            all_done = self._all_concepts_done_or_skipped(session)
            decision = decide_on_command(
                session.state, command,
                session.current_concept_index,
                len(session.what_list),
                all_done,
            )

            if decision.action == "abandon_and_restart":
                async for event in self._run_restart(session, node_meta):
                    yield event
                return

            if decision.mark_skipped:
                idx = str(session.current_concept_index)
                skipped_concept = session.what_list[session.current_concept_index] if session.current_concept_index < len(session.what_list) else ""
                session.concepts_status[idx] = "skipped"
                with get_db_context() as db:
                    update_session(db, session.id, concepts_status=session.concepts_status)
                yield _sse("concept_update", index=session.current_concept_index, status="skipped")
                self.memory_updater.fire(
                    MemoryEvent(
                        user_id=session.user_id,
                        session_id=session.id,
                        node_id=session.node_id,
                        event_type="concept_skipped",
                        payload={"concept": skipped_concept},
                    ),
                    background_tasks,
                )

            if decision.advance_concept:
                session.current_concept_index += 1
                with get_db_context() as db:
                    update_session(db, session.id, current_concept_index=session.current_concept_index)
                new_idx = str(session.current_concept_index)
                session.concepts_status[new_idx] = "current"
                with get_db_context() as db:
                    update_session(db, session.id, concepts_status=session.concepts_status)
                yield _sse("concept_update", index=session.current_concept_index, status="current")

            if decision.action == "teach":
                async for event in self._run_teach(session, node_meta, mode=decision.teach_mode, background_tasks=background_tasks, language=language):
                    yield event

            elif decision.action == "check_readiness":
                async for event in self._run_readiness(session, node_meta, background_tasks=background_tasks, language=language):
                    yield event

            elif decision.action == "show_test_confirm":
                with get_db_context() as db:
                    update_session(db, session.id, state="CONFIRMING_TEST")
                yield _sse("state_change", **{"from": session.state, "to": "CONFIRMING_TEST"})
                yield _sse("test_confirm_prompt",
                           message=(
                               "你已完成所有概念的学习！准备好进行综合测试了吗？"
                               if language == "zh-CN"
                               else "You have completed every concept. Ready for the comprehensive quiz?"
                           ),
                           commands=["confirm_test", "not_ready"])
                session.state = "CONFIRMING_TEST"

            elif decision.action == "generate_test_questions":
                async for event in self._run_generate_test(session, node_meta, language=language):
                    yield event

            elif decision.action in ("wait_user",):
                pass

            else:
                yield _sse("error", error={"code": "UNKNOWN_ACTION", "message": decision.action})

        except Exception as e:
            logger.exception("stream_command error")
            yield _sse("error", error={"code": "INTERNAL_ERROR", "message": str(e)})
        finally:
            yield _sse("done")

    # ── internal helpers ──────────────────────────────────────────────────────

    def _all_concepts_done_or_skipped(self, session: SessionState) -> bool:
        for i in range(len(session.what_list)):
            status = session.concepts_status.get(str(i), "pending")
            if status not in ("done", "skipped"):
                return False
        return True

    @staticmethod
    def _display_concepts(session: SessionState, node_meta: dict) -> list[str]:
        localized = node_meta.get("what_list") or []
        return localized if len(localized) == len(session.what_list) else session.what_list

    def _count_images_in_turns(self, session: SessionState) -> int:
        return sum(
            1 for m in session.recent_turns
            if m.get("kind") in ("mermaid", "dalle_image")
        )

    async def _run_teach(
        self, session: SessionState, node_meta: dict, mode: TeachingMode,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        prev_state = session.state
        with get_db_context() as db:
            update_session(db, session.id, state="TEACHING")
        yield _sse("state_change", **{"from": prev_state, "to": "TEACHING"})
        session.state = "TEACHING"

        idx = session.current_concept_index
        concepts = self._display_concepts(session, node_meta)
        current_concept = concepts[idx] if idx < len(concepts) else ""

        # Build memory context
        memory_context = ""
        try:
            with get_db_context() as db:
                memory_context = self.memory_builder.build(db, session.user_id, session.node_id, session)
        except Exception as e:
            logger.warning("memory_builder.build failed (non-fatal): %s", e)

        yield _sse("assistant_start")
        streamed_content = ""
        try:
            output = None
            async for item in self.teaching_agent.stream_run(
                    node_name=node_meta["node_name"],
                    node_why=node_meta["node_why"],
                    current_concept=current_concept,
                    concept_index=idx,
                    total_concepts=len(concepts),
                    difficulty_level=session.difficulty_level,
                    weak_points=session.weak_points,
                    recent_turns=session.recent_turns[-8:],
                    mode=mode,
                    memory_context=memory_context,
                    language=language,
            ):
                if item.get("type") == "content":
                    text = item.get("text", "")
                    streamed_content += text
                    yield _sse("chunk", text=text)
                elif item.get("type") == "done":
                    output = item.get("output")
            if output is None:
                raise ValueError("teaching stream ended without output")
        except Exception as e:
            logger.error("TeachingAgent.run raised: %s", e)
            yield _sse("error", error={"code": "AI_ERROR", "message": str(e)})
            yield _sse("done")
            return

        if not streamed_content:
            for chunk in _split_text_for_streaming(output.content):
                yield _sse("chunk", text=chunk)
                await asyncio.sleep(0)

        # Image trigger (Phase 2)
        image_turns: list[dict] = []
        try:
            prev_img_count = self._count_images_in_turns(session)
            trigger = await self.image_trigger.decide(
                teaching_content=output.content,
                concept=current_concept,
                node_name=node_meta["node_name"],
                previous_image_count=prev_img_count,
            )
            if trigger.needs_image:
                if trigger.image_type == "mermaid" and trigger.mermaid_code:
                    yield _sse("image_mermaid", code=trigger.mermaid_code)
                    image_turns.append({
                        "role": "assistant",
                        "kind": "mermaid",
                        "content": trigger.mermaid_code,
                        "reason": trigger.reason,
                    })
                elif trigger.image_type == "dalle" and trigger.dalle_prompt:
                    img_id = str(uuid4())
                    yield _sse("image_dalle_pending", id=img_id, reason=trigger.reason)
                    try:
                        llm = get_llm_client()
                        img_bytes = await llm.generate_image(prompt=trigger.dalle_prompt)
                        url = await image_storage.upload_image(session.user_id, session.id, img_bytes)
                        yield _sse("image_dalle_done", id=img_id, url=url)
                        if url:
                            image_turns.append({
                                "role": "assistant",
                                "kind": "dalle_image",
                                "content": url,
                                "reason": trigger.reason,
                            })
                    except Exception as img_err:
                        logger.warning("dalle generation failed: %s", img_err)
                        yield _sse("image_dalle_done", id=img_id, url="")
        except Exception as e:
            logger.warning("image_trigger failed (non-fatal): %s", e)

        # Notes suggestion
        try:
            snippet = _maybe_emit_note_suggestion(output.content)
            if snippet:
                yield _sse("notes_suggestion", snippet=snippet)
        except Exception as e:
            logger.warning("notes_suggestion failed (non-fatal): %s", e)

        assistant_turns = [{"role": "assistant", "kind": "text", "content": output.content}]
        if output.questions:
            assistant_turns.append({
                "role": "assistant",
                "kind": "questions",
                "content": output.questions,
            })
        assistant_turns.extend(image_turns)
        new_turns = (session.recent_turns + assistant_turns)[-8:]
        session.recent_turns = new_turns

        # Mark current concept as "current" if it's still pending
        cs = dict(session.concepts_status)
        if cs.get(str(idx), "pending") == "pending":
            cs[str(idx)] = "current"
            session.concepts_status = cs
            yield _sse("concept_update", index=idx, status="current")

        with get_db_context() as db:
            update_session(db, session.id,
                           state="QUESTIONING",
                           recent_turns=new_turns,
                           concepts_status=session.concepts_status)

        yield _sse("state_change", **{"from": "TEACHING", "to": "QUESTIONING"})
        session.state = "QUESTIONING"

        if output.questions:
            yield _sse("questions", items=output.questions)

    async def _run_assessment(
        self, session: SessionState, node_meta: dict, user_answer: str, is_test: bool,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        prev_state = session.state
        new_state = "EVALUATING_TEST" if is_test else "EVALUATING"
        with get_db_context() as db:
            update_session(db, session.id, state=new_state)
        yield _sse("state_change", **{"from": prev_state, "to": new_state})
        session.state = new_state

        idx = session.current_concept_index
        concepts = self._display_concepts(session, node_meta)
        current_concept = concepts[idx] if idx < len(concepts) else ""

        if is_test:
            q_idx = session.test_current_index
            question = session.test_questions[q_idx] if q_idx < len(session.test_questions) else current_concept
        else:
            question = current_concept

        try:
            result = await self.assessment_per_q.run(
                concept=current_concept,
                question=question,
                user_answer=user_answer,
                prev_wrong_count=session.wrong_count_current,
                weak_points=session.weak_points,
                language=language,
            )
        except Exception as e:
            logger.error("AssessmentPerQuestionAgent raised: %s", e)
            yield _sse("error", error={"code": "AI_ERROR", "message": str(e)})
            return

        yield _sse("assessment",
                   is_correct=result.is_correct,
                   explanation=result.explanation,
                   feedback=result.feedback)

        new_weak = list(session.weak_points)
        for w in result.update_weak_points:
            if w not in new_weak:
                new_weak.append(w)

        new_diff = max(1, min(5, session.difficulty_level + result.difficulty_delta))

        if is_test:
            test_results = session.test_results + [{
                "question": question,
                "answer": user_answer,
                "is_correct": result.is_correct,
                "feedback": result.feedback,
            }]
            session.test_results = test_results

            decision = decide_on_assessment_done(
                "EVALUATING_TEST", result.is_correct, result.wrong_count,
                session.test_current_index, test_total=3,
            )

            if decision.action == "emit_next_test_q":
                new_idx = session.test_current_index + 1
                with get_db_context() as db:
                    update_session(db, session.id,
                                   state="TESTING",
                                   test_current_index=new_idx,
                                   test_results=test_results,
                                   weak_points=new_weak,
                                   difficulty_level=new_diff)
                session.test_current_index = new_idx
                session.weak_points = new_weak
                session.difficulty_level = new_diff
                yield _sse("state_change", **{"from": "EVALUATING_TEST", "to": "TESTING"})
                session.state = "TESTING"
                next_q = session.test_questions[new_idx] if new_idx < len(session.test_questions) else ""
                yield _sse("questions", items=[next_q])

            elif decision.action == "final_judge":
                with get_db_context() as db:
                    update_session(db, session.id,
                                   test_results=test_results,
                                   weak_points=new_weak,
                                   difficulty_level=new_diff)
                session.weak_points = new_weak
                async for event in self._run_final_judge(session, node_meta, background_tasks=background_tasks, language=language):
                    yield event
        else:
            session.wrong_count_current = result.wrong_count

            decision = decide_on_assessment_done(
                "EVALUATING", result.is_correct, result.wrong_count, 0
            )

            if result.is_correct:
                # Memory: concept passed
                self.memory_updater.fire(
                    MemoryEvent(
                        user_id=session.user_id, session_id=session.id, node_id=session.node_id,
                        event_type="concept_passed", payload={"concept": current_concept},
                    ),
                    background_tasks,
                )
                cs = dict(session.concepts_status)
                cs[str(idx)] = "done"
                session.concepts_status = cs
                with get_db_context() as db:
                    update_session(db, session.id,
                                   state="AWAITING_COMMAND",
                                   wrong_count_current=0,
                                   concepts_status=cs,
                                   weak_points=new_weak,
                                   difficulty_level=new_diff)
                session.wrong_count_current = 0
                session.weak_points = new_weak
                session.difficulty_level = new_diff
                yield _sse("concept_update", index=idx, status="done")

                is_last_concept = idx == len(concepts) - 1
                if is_last_concept and self._all_concepts_done_or_skipped(session):
                    async for event in self._run_readiness(
                        session, node_meta, background_tasks=background_tasks, language=language,
                    ):
                        yield event
                else:
                    with get_db_context() as db:
                        update_session(db, session.id, state="AWAITING_COMMAND")
                    yield _sse("state_change", **{"from": "EVALUATING", "to": "AWAITING_COMMAND"})
                    session.state = "AWAITING_COMMAND"
                    yield _sse("show_commands", commands=["continue", "expand", "skip", "reteach"])

            elif decision.action == "teach":
                cs = dict(session.concepts_status)
                cs[str(idx)] = "failed"
                session.concepts_status = cs
                if result.wrong_count >= 2:
                    self.memory_updater.fire(
                        MemoryEvent(
                            user_id=session.user_id, session_id=session.id, node_id=session.node_id,
                            event_type="concept_failed_twice", payload={"concept": current_concept},
                        ),
                        background_tasks,
                    )
                with get_db_context() as db:
                    update_session(db, session.id,
                                   wrong_count_current=result.wrong_count,
                                   concepts_status=cs,
                                   weak_points=new_weak,
                                   difficulty_level=new_diff)
                session.wrong_count_current = result.wrong_count
                session.weak_points = new_weak
                session.difficulty_level = new_diff
                yield _sse("concept_update", index=idx, status="failed")
                async for event in self._run_teach(session, node_meta, mode="probe_stuck", background_tasks=background_tasks, language=language):
                    yield event

            else:
                cs = dict(session.concepts_status)
                cs[str(idx)] = "failed"
                session.concepts_status = cs
                with get_db_context() as db:
                    update_session(db, session.id,
                                   state="AWAITING_COMMAND",
                                   wrong_count_current=result.wrong_count,
                                   concepts_status=cs,
                                   weak_points=new_weak,
                                   difficulty_level=new_diff)
                session.wrong_count_current = result.wrong_count
                session.weak_points = new_weak
                session.difficulty_level = new_diff
                yield _sse("concept_update", index=idx, status="failed")
                yield _sse("state_change", **{"from": "EVALUATING", "to": "AWAITING_COMMAND"})
                session.state = "AWAITING_COMMAND"
                yield _sse("show_commands", commands=["continue", "expand", "skip", "reteach"])

    async def _run_readiness(
        self, session: SessionState, node_meta: dict,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        prev_state = session.state
        with get_db_context() as db:
            update_session(db, session.id, state="AI_ASSESSING_READINESS")
        yield _sse("state_change", **{"from": prev_state, "to": "AI_ASSESSING_READINESS"})
        session.state = "AI_ASSESSING_READINESS"

        concepts = self._display_concepts(session, node_meta)
        done = [concepts[i] for i in range(len(concepts)) if session.concepts_status.get(str(i)) == "done"]
        skipped = [concepts[i] for i in range(len(concepts)) if session.concepts_status.get(str(i)) == "skipped"]

        try:
            result = await self.assessment_overall.run_readiness(
                node_name=node_meta["node_name"],
                concepts_done=done,
                concepts_skipped=skipped,
                weak_points=session.weak_points,
                language=language,
            )
        except Exception as e:
            logger.error("run_readiness raised: %s", e)
            yield _sse("error", error={"code": "AI_ERROR", "message": str(e)})
            return

        decision = decide_on_readiness_done(result.ready_for_test)

        if decision.action == "show_test_confirm":
            with get_db_context() as db:
                update_session(db, session.id, state="CONFIRMING_TEST")
            yield _sse("state_change", **{"from": "AI_ASSESSING_READINESS", "to": "CONFIRMING_TEST"})
            session.state = "CONFIRMING_TEST"
            yield _sse("test_confirm_prompt",
                       message=(
                           f"综合评估：{result.reason} 准备好进行综合测试了吗？"
                           if language == "zh-CN"
                           else f"Readiness check: {result.reason} Ready for the comprehensive quiz?"
                       ),
                       commands=["confirm_test", "not_ready"])
        else:
            async for event in self._run_teach(session, node_meta, mode="review_weak", background_tasks=background_tasks, language=language):
                yield event

    async def _run_generate_test(
        self, session: SessionState, node_meta: dict,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        prev_state = session.state
        with get_db_context() as db:
            update_session(db, session.id, state="TESTING")
        yield _sse("state_change", **{"from": prev_state, "to": "TESTING"})
        session.state = "TESTING"

        questions = await _generate_test_questions(
            node_meta["node_name"], self._display_concepts(session, node_meta), session.weak_points, language
        )
        session.test_questions = questions
        session.test_current_index = 0
        session.test_results = []
        with get_db_context() as db:
            update_session(db, session.id,
                           test_questions=questions,
                           test_current_index=0,
                           test_results=[])
        yield _sse("questions", items=[questions[0]])

    async def _run_final_judge(
        self, session: SessionState, node_meta: dict,
        background_tasks: Optional[BackgroundTasks] = None,
        language: str = "zh-CN",
    ) -> AsyncGenerator[str, None]:
        try:
            result = await self.assessment_overall.run_final_judge(
                node_name=node_meta["node_name"],
                test_qa_pairs=session.test_results,
                weak_points=session.weak_points,
                language=language,
            )
        except Exception as e:
            logger.error("run_final_judge raised: %s", e)
            yield _sse("error", error={"code": "AI_ERROR", "message": str(e)})
            return

        decision = decide_on_final_judge(result.passed)

        # Determine concepts covered (all that are "done")
        display_concepts = self._display_concepts(session, node_meta)
        concepts_covered = [
            display_concepts[i]
            for i in range(len(display_concepts))
            if session.concepts_status.get(str(i)) == "done"
        ]

        if decision.action == "generate_note":
            # Transition to GENERATING_NOTE immediately
            with get_db_context() as db:
                update_session(db, session.id, state="GENERATING_NOTE")
            yield _sse("state_change", **{"from": session.state, "to": "GENERATING_NOTE"})
            session.state = "GENERATING_NOTE"
            yield _sse("note_generating")

            # Generate the completion note (failure is non-fatal)
            note_id: Optional[str] = None
            try:
                localized_session = session.model_copy(update={"what_list": display_concepts})
                note_output = await self.note_generator.generate(
                    session=localized_session,
                    node_name=node_meta.get("node_name", ""),
                    node_why=node_meta.get("node_why", ""),
                    language=language,
                )
                with get_db_context() as db:
                    note_id = save_completion_note(
                        db,
                        user_id=session.user_id,
                        node_id=session.node_id,
                        session_id=session.id,
                        content=note_output.content,
                    )
            except Exception:
                logger.exception("Note generation failed (non-fatal) — completing session without note")

            # Mark node learned and complete session
            with get_db_context() as db:
                db.execute("UPDATE nodes SET status='learned' WHERE id=?", (session.node_id,))
                db.commit()
                update_session(db, session.id,
                               state="COMPLETED",
                               status="completed",
                               ended_at=datetime.now(timezone.utc))
            yield _sse("state_change", **{"from": "GENERATING_NOTE", "to": "COMPLETED"})
            session.state = "COMPLETED"

            if note_id:
                yield _sse("note_ready", note_id=note_id)

            yield _sse("node_completed", node_id=session.node_id)

            # Memory: test passed
            self.memory_updater.fire(
                MemoryEvent(
                    user_id=session.user_id, session_id=session.id, node_id=session.node_id,
                    event_type="test_passed",
                    payload={
                        "plan_id": session.plan_id,
                        "concepts_covered": concepts_covered,
                        "weak_points": session.weak_points,
                        "test_results": session.test_results,
                        "conversation_turns": len(session.recent_turns),
                    },
                ),
                background_tasks,
            )
        else:
            with get_db_context() as db:
                update_session(db, session.id, state="CHOOSING_AFTER_FAIL")
            yield _sse("state_change", **{"from": session.state, "to": "CHOOSING_AFTER_FAIL"})
            session.state = "CHOOSING_AFTER_FAIL"
            weak_str = (
                "、".join(result.weak_areas) if result.weak_areas else "部分概念"
            ) if language == "zh-CN" else (
                ", ".join(result.weak_areas) if result.weak_areas else "some concepts"
            )
            yield _sse("fail_options",
                       message=(
                           f"综合评估未通过。{result.reason} 薄弱点：{weak_str}"
                           if language == "zh-CN"
                           else f"The comprehensive assessment was not passed. {result.reason} Review: {weak_str}."
                       ),
                       options=[
                           {"command": "restart", "label": "🔄 重新开始" if language == "zh-CN" else "🔄 Start over"},
                           {"command": "not_ready", "label": "📚 针对弱点复习" if language == "zh-CN" else "📚 Review weak areas"},
                       ])
            # Memory: test failed
            self.memory_updater.fire(
                MemoryEvent(
                    user_id=session.user_id, session_id=session.id, node_id=session.node_id,
                    event_type="test_failed",
                    payload={
                        "plan_id": session.plan_id,
                        "concepts_covered": concepts_covered,
                        "weak_points": session.weak_points,
                        "conversation_turns": len(session.recent_turns),
                    },
                ),
                background_tasks,
            )

    async def _run_restart(
        self, session: SessionState, node_meta: dict,
    ) -> AsyncGenerator[str, None]:
        with get_db_context() as db:
            abandon_session(db, session.id)
            new_session = create_session(
                db,
                user_id=session.user_id,
                node_id=session.node_id,
                plan_id=session.plan_id,
                what_list=session.what_list,
            )
        yield _sse("restart", new_session_id=new_session.id)
