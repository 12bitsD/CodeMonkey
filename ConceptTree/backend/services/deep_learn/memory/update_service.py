"""MemoryUpdateService — event dispatcher per §0.5 trigger table."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import BackgroundTasks

from database import get_db_context
from models_memory import EpisodicRecord, MemoryEvent
from services.deep_learn.memory import repository as repo

logger = logging.getLogger(__name__)

PROCEDURAL_AGGREGATION_MIN_SESSIONS = 3
PROCEDURAL_AGGREGATION_INTERVAL = 5


def _should_aggregate_procedural(session_count: int) -> bool:
    if session_count < PROCEDURAL_AGGREGATION_MIN_SESSIONS:
        return False
    return (
        session_count == PROCEDURAL_AGGREGATION_MIN_SESSIONS
        or session_count % PROCEDURAL_AGGREGATION_INTERVAL == 0
    )


class MemoryUpdateService:
    def fire(
        self,
        event: MemoryEvent,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> None:
        try:
            with get_db_context() as db:
                if event.event_type == "concept_passed":
                    concept = event.payload.get("concept", "")
                    if concept:
                        repo.add_mastered_concept(db, event.user_id, concept, event.node_id)

                elif event.event_type == "concept_failed_twice":
                    concept = event.payload.get("concept", "")
                    if concept:
                        repo.upsert_weak_concept(db, event.user_id, concept, event.node_id)

                elif event.event_type == "concept_skipped":
                    logger.info(
                        "concept skipped: %s (user=%s)", event.payload.get("concept"), event.user_id
                    )

                elif event.event_type in ("test_passed", "test_failed"):
                    self._dispatch_background(
                        self._run_session_memory_update,
                        event,
                        background_tasks=background_tasks,
                    )

                elif event.event_type == "session_completed":
                    if not repo.has_episodic_record(db, event.session_id):
                        self._dispatch_background(
                            self._run_session_memory_update,
                            event,
                            background_tasks=background_tasks,
                        )

        except Exception as e:
            logger.error("MemoryUpdateService.fire failed: %s", e, exc_info=True)

    def _dispatch_background(
        self,
        task_func,
        *args,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> None:
        if background_tasks is not None:
            background_tasks.add_task(task_func, *args)
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(task_func(*args))
            return

        loop.create_task(task_func(*args))

    def _build_episodic_record(self, event: MemoryEvent) -> EpisodicRecord:
        payload = event.payload
        now = datetime.now(timezone.utc).isoformat()
        return EpisodicRecord(
            id=str(uuid4()),
            user_id=event.user_id,
            node_id=event.node_id,
            plan_id=payload.get("plan_id", ""),
            session_id=event.session_id,
            summary="",  # filled async by update_agent
            concepts_covered=payload.get("concepts_covered", []),
            weak_points=payload.get("weak_points", []),
            strong_points=payload.get("strong_points", []),
            test_score=payload.get("test_score"),
            passed=(event.event_type == "test_passed"),
            conversation_turns=payload.get("conversation_turns", 0),
            created_at=now,
        )

    async def _run_session_memory_update(self, event: MemoryEvent) -> None:
        try:
            from services.deep_learn.memory.update_agent import MemoryUpdateAgent

            record = self._build_episodic_record(event)
            agent = MemoryUpdateAgent()
            summary = await agent.summarize(
                session_data=event.payload,
                concepts_covered=record.concepts_covered,
                test_results=event.payload.get("test_results", []),
            )
            record.summary = summary

            with get_db_context() as db:
                repo.write_episodic_record(db, record)
                if event.event_type == "test_passed":
                    for concept in record.concepts_covered:
                        repo.add_mastered_concept(db, event.user_id, concept, event.node_id)
                session_count = repo.count_completed_sessions(db, event.user_id)

            if _should_aggregate_procedural(session_count):
                await self._run_procedural_aggregation(event.user_id, session_count)
        except Exception as e:
            logger.error("_run_session_memory_update failed: %s", e, exc_info=True)

    async def _run_procedural_aggregation(self, user_id: str, session_count: int) -> None:
        try:
            from services.deep_learn.memory.update_agent import MemoryUpdateAgent
            agent = MemoryUpdateAgent()
            with get_db_context() as db:
                records = repo.get_all_episodic_since(db, user_id, since_count=5)
                if not records:
                    return
                patterns = await agent.aggregate_procedural(recent_records=records)
                for p in patterns:
                    repo.upsert_procedural_pattern(db, user_id, p.pattern_key, p.pattern_value, p.confidence)
        except Exception as e:
            logger.error("_run_procedural_aggregation failed: %s", e, exc_info=True)
