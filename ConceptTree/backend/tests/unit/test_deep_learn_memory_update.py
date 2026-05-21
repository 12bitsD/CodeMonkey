import pytest

from models_memory import MemoryEvent
from services.deep_learn.memory.update_service import (
    MemoryUpdateService,
    _should_aggregate_procedural,
)


pytestmark = pytest.mark.no_db


def test_procedural_aggregation_schedule_starts_at_three_then_every_five():
    assert _should_aggregate_procedural(0) is False
    assert _should_aggregate_procedural(2) is False
    assert _should_aggregate_procedural(3) is True
    assert _should_aggregate_procedural(4) is False
    assert _should_aggregate_procedural(5) is True
    assert _should_aggregate_procedural(10) is True


def test_test_result_event_schedules_session_memory_update(monkeypatch):
    class FakeDbContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    class FakeBackgroundTasks:
        def __init__(self):
            self.tasks = []

        def add_task(self, func, *args, **kwargs):
            self.tasks.append((func, args, kwargs))

    monkeypatch.setattr(
        "services.deep_learn.memory.update_service.get_db_context",
        lambda: FakeDbContext(),
    )

    service = MemoryUpdateService()
    background_tasks = FakeBackgroundTasks()
    event = MemoryEvent(
        user_id="user-1",
        session_id="session-1",
        node_id="node-1",
        event_type="test_passed",
        payload={"concepts_covered": ["concept-a"], "test_results": []},
    )

    service.fire(event, background_tasks)

    assert len(background_tasks.tasks) == 1
    func, args, kwargs = background_tasks.tasks[0]
    assert func == service._run_session_memory_update
    assert args == (event,)
    assert kwargs == {}
